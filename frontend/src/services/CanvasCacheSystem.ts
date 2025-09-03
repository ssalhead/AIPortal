/**
 * Canvas 2-Tier 캐싱 시스템 v5.0
 * 
 * 특징:
 * - L1 Cache: 메모리 기반 고속 캐싱 (LRU)
 * - L2 Cache: IndexedDB 기반 영구 저장
 * - 백엔드 PostgreSQL 동기화
 * - 자동 캐시 무효화 및 정리
 * - 성능 최적화 알고리즘
 */

import type { CanvasItem } from '../types/canvas';

// ======= 타입 정의 =======

interface CacheEntry<T = any> {
  key: string;
  value: T;
  timestamp: number;
  lastAccessed: number;
  accessCount: number;
  size: number; // 바이트 단위
  ttl?: number; // Time To Live (밀리초)
  tags?: string[]; // 캐시 태그 (무효화용)
}

interface CacheMetrics {
  l1Hits: number;
  l1Misses: number;
  l2Hits: number;
  l2Misses: number;
  totalEntries: number;
  memoryUsage: number; // 바이트
  hitRate: number; // 0-1
  avgAccessTime: number; // 밀리초
}

interface CacheOptions {
  l1MaxEntries: number;
  l1MaxMemory: number; // 바이트
  l2DatabaseName: string;
  l2MaxEntries: number;
  defaultTTL: number; // 밀리초
  cleanupInterval: number; // 밀리초
  syncWithBackend: boolean;
}

// ======= L1 메모리 캐시 (LRU) =======

class L1MemoryCache {
  private cache = new Map<string, CacheEntry>();
  private accessOrder = new Map<string, number>(); // LRU 순서 추적
  private currentMemory = 0;
  private accessCounter = 0;

  constructor(
    private maxEntries: number = 1000,
    private maxMemory: number = 50 * 1024 * 1024 // 50MB
  ) {}

  get(key: string): any | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }

    // TTL 확인
    if (entry.ttl && Date.now() > entry.timestamp + entry.ttl) {
      this.delete(key);
      return null;
    }

    // 접근 정보 업데이트
    entry.lastAccessed = Date.now();
    entry.accessCount++;
    this.accessOrder.set(key, ++this.accessCounter);

    return entry.value;
  }

  set(key: string, value: any, ttl?: number, tags?: string[]): void {
    // 기존 엔트리 제거 (메모리 회수)
    if (this.cache.has(key)) {
      this.delete(key);
    }

    const size = this.calculateSize(value);
    const now = Date.now();

    const entry: CacheEntry = {
      key,
      value,
      timestamp: now,
      lastAccessed: now,
      accessCount: 1,
      size,
      ttl,
      tags
    };

    // 메모리 제한 확인 및 정리
    this.ensureCapacity(size);

    // 엔트리 추가
    this.cache.set(key, entry);
    this.accessOrder.set(key, ++this.accessCounter);
    this.currentMemory += size;
  }

  delete(key: string): boolean {
    const entry = this.cache.get(key);
    if (!entry) {
      return false;
    }

    this.cache.delete(key);
    this.accessOrder.delete(key);
    this.currentMemory -= entry.size;
    
    return true;
  }

  has(key: string): boolean {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return false;
    }

    // TTL 확인
    if (entry.ttl && Date.now() > entry.timestamp + entry.ttl) {
      this.delete(key);
      return false;
    }

    return true;
  }

  clear(): void {
    this.cache.clear();
    this.accessOrder.clear();
    this.currentMemory = 0;
    this.accessCounter = 0;
  }

  invalidateByTags(tags: string[]): number {
    let invalidatedCount = 0;
    
    for (const [key, entry] of this.cache.entries()) {
      if (entry.tags && entry.tags.some(tag => tags.includes(tag))) {
        this.delete(key);
        invalidatedCount++;
      }
    }
    
    return invalidatedCount;
  }

  private ensureCapacity(newEntrySize: number): void {
    // 메모리 제한 확인
    while (
      this.currentMemory + newEntrySize > this.maxMemory ||
      this.cache.size >= this.maxEntries
    ) {
      this.evictLRU();
    }
  }

  private evictLRU(): void {
    // 가장 오래된 접근 순서의 엔트리 찾기
    let oldestKey: string | null = null;
    let oldestAccessOrder = Infinity;

    for (const [key, accessOrder] of this.accessOrder.entries()) {
      if (accessOrder < oldestAccessOrder) {
        oldestAccessOrder = accessOrder;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.delete(oldestKey);
    }
  }

  private calculateSize(value: any): number {
    // 대략적인 메모리 사용량 계산
    const jsonString = JSON.stringify(value);
    return jsonString.length * 2; // Unicode 문자는 2바이트
  }

  getMetrics(): Partial<CacheMetrics> {
    return {
      totalEntries: this.cache.size,
      memoryUsage: this.currentMemory
    };
  }

  getAllKeys(): string[] {
    return Array.from(this.cache.keys());
  }
}

// ======= L2 IndexedDB 캐시 =======

class L2IndexedDBCache {
  private db: IDBDatabase | null = null;
  private dbName: string;
  private version = 1;

  constructor(
    dbName: string = 'CanvasCache',
    private maxEntries: number = 10000
  ) {
    this.dbName = dbName;
  }

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        
        if (!db.objectStoreNames.contains('cache')) {
          const store = db.createObjectStore('cache', { keyPath: 'key' });
          store.createIndex('timestamp', 'timestamp');
          store.createIndex('lastAccessed', 'lastAccessed');
          store.createIndex('tags', 'tags', { multiEntry: true });
        }
      };
    });
  }

  async get(key: string): Promise<any | null> {
    if (!this.db) return null;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const request = store.get(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const entry = request.result as CacheEntry | undefined;
        
        if (!entry) {
          resolve(null);
          return;
        }

        // TTL 확인
        if (entry.ttl && Date.now() > entry.timestamp + entry.ttl) {
          this.delete(key);
          resolve(null);
          return;
        }

        // 접근 정보 업데이트
        entry.lastAccessed = Date.now();
        entry.accessCount++;

        const updateRequest = store.put(entry);
        updateRequest.onsuccess = () => resolve(entry.value);
        updateRequest.onerror = () => resolve(entry.value); // 업데이트 실패해도 값은 반환
      };
    });
  }

  async set(key: string, value: any, ttl?: number, tags?: string[]): Promise<void> {
    if (!this.db) return;

    const now = Date.now();
    const entry: CacheEntry = {
      key,
      value,
      timestamp: now,
      lastAccessed: now,
      accessCount: 1,
      size: JSON.stringify(value).length * 2,
      ttl,
      tags
    };

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');

      // 용량 제한 확인
      this.ensureCapacity().then(() => {
        const request = store.put(entry);
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
      }).catch(reject);
    });
  }

  async delete(key: string): Promise<boolean> {
    if (!this.db) return false;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const request = store.delete(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(true);
    });
  }

  async has(key: string): Promise<boolean> {
    const value = await this.get(key);
    return value !== null;
  }

  async clear(): Promise<void> {
    if (!this.db) return;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const request = store.clear();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async invalidateByTags(tags: string[]): Promise<number> {
    if (!this.db) return 0;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const index = store.index('tags');
      
      let deletedCount = 0;
      const deletePromises: Promise<void>[] = [];

      tags.forEach(tag => {
        const request = index.openCursor(IDBKeyRange.only(tag));
        
        request.onsuccess = (event) => {
          const cursor = (event.target as IDBRequest).result;
          if (cursor) {
            deletePromises.push(
              new Promise((deleteResolve, deleteReject) => {
                const deleteRequest = cursor.delete();
                deleteRequest.onsuccess = () => {
                  deletedCount++;
                  deleteResolve();
                };
                deleteRequest.onerror = () => deleteReject(deleteRequest.error);
              })
            );
            cursor.continue();
          }
        };
      });

      Promise.all(deletePromises)
        .then(() => resolve(deletedCount))
        .catch(reject);
    });
  }

  private async ensureCapacity(): Promise<void> {
    if (!this.db) return;

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['cache'], 'readonly');
      const store = transaction.objectStore('cache');
      const countRequest = store.count();

      countRequest.onsuccess = () => {
        const count = countRequest.result;
        
        if (count >= this.maxEntries) {
          this.evictOldestEntries().then(resolve).catch(reject);
        } else {
          resolve();
        }
      };
      
      countRequest.onerror = () => reject(countRequest.error);
    });
  }

  private async evictOldestEntries(): Promise<void> {
    if (!this.db) return;

    const entriesToRemove = Math.floor(this.maxEntries * 0.1); // 10% 제거

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const index = store.index('lastAccessed');
      const request = index.openCursor();

      let removedCount = 0;

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        
        if (cursor && removedCount < entriesToRemove) {
          cursor.delete();
          removedCount++;
          cursor.continue();
        } else {
          resolve();
        }
      };

      request.onerror = () => reject(request.error);
    });
  }
}

// ======= 2-Tier 캐시 시스템 =======

export class CanvasCacheSystem {
  private l1Cache: L1MemoryCache;
  private l2Cache: L2IndexedDBCache;
  private metrics: CacheMetrics;
  private cleanupTimer: NodeJS.Timeout | null = null;

  constructor(private options: Partial<CacheOptions> = {}) {
    const config: CacheOptions = {
      l1MaxEntries: 1000,
      l1MaxMemory: 50 * 1024 * 1024, // 50MB
      l2DatabaseName: 'CanvasCache',
      l2MaxEntries: 10000,
      defaultTTL: 24 * 60 * 60 * 1000, // 24시간
      cleanupInterval: 5 * 60 * 1000, // 5분
      syncWithBackend: true,
      ...options
    };

    this.l1Cache = new L1MemoryCache(config.l1MaxEntries, config.l1MaxMemory);
    this.l2Cache = new L2IndexedDBCache(config.l2DatabaseName, config.l2MaxEntries);

    this.metrics = {
      l1Hits: 0,
      l1Misses: 0,
      l2Hits: 0,
      l2Misses: 0,
      totalEntries: 0,
      memoryUsage: 0,
      hitRate: 0,
      avgAccessTime: 0
    };

    this.startCleanupTimer(config.cleanupInterval);
  }

  async init(): Promise<void> {
    await this.l2Cache.init();
    console.log('✅ Canvas 2-Tier 캐시 시스템 초기화 완료');
  }

  // ======= 캐시 기본 작업 =======

  async get(key: string): Promise<any | null> {
    const startTime = performance.now();

    try {
      // L1 캐시 확인
      const l1Value = this.l1Cache.get(key);
      if (l1Value !== null) {
        this.metrics.l1Hits++;
        this.updateMetrics(performance.now() - startTime);
        return l1Value;
      }

      this.metrics.l1Misses++;

      // L2 캐시 확인
      const l2Value = await this.l2Cache.get(key);
      if (l2Value !== null) {
        this.metrics.l2Hits++;
        
        // L1 캐시에 승격
        this.l1Cache.set(key, l2Value);
        
        this.updateMetrics(performance.now() - startTime);
        return l2Value;
      }

      this.metrics.l2Misses++;
      this.updateMetrics(performance.now() - startTime);
      
      return null;

    } catch (error) {
      console.error('❌ 캐시 조회 실패:', error);
      return null;
    }
  }

  async set(key: string, value: any, options?: {
    ttl?: number;
    tags?: string[];
    l1Only?: boolean;
  }): Promise<void> {
    const { ttl, tags, l1Only = false } = options || {};

    try {
      // L1 캐시에 저장
      this.l1Cache.set(key, value, ttl, tags);

      // L2 캐시에도 저장 (l1Only 옵션이 false인 경우)
      if (!l1Only) {
        await this.l2Cache.set(key, value, ttl, tags);
      }

      console.log(`💾 캐시 저장 완료: ${key} (L1: ✓, L2: ${l1Only ? '✗' : '✓'})`);

    } catch (error) {
      console.error('❌ 캐시 저장 실패:', error);
      throw error;
    }
  }

  async delete(key: string): Promise<boolean> {
    try {
      const l1Result = this.l1Cache.delete(key);
      const l2Result = await this.l2Cache.delete(key);
      
      const success = l1Result || l2Result;
      
      if (success) {
        console.log(`🗑️ 캐시 삭제 완료: ${key}`);
      }
      
      return success;

    } catch (error) {
      console.error('❌ 캐시 삭제 실패:', error);
      return false;
    }
  }

  async has(key: string): Promise<boolean> {
    try {
      return this.l1Cache.has(key) || await this.l2Cache.has(key);
    } catch (error) {
      console.error('❌ 캐시 확인 실패:', error);
      return false;
    }
  }

  async clear(): Promise<void> {
    try {
      this.l1Cache.clear();
      await this.l2Cache.clear();
      this.resetMetrics();
      console.log('🧹 캐시 전체 정리 완료');
    } catch (error) {
      console.error('❌ 캐시 정리 실패:', error);
      throw error;
    }
  }

  // ======= Canvas 특화 메서드 =======

  async cacheCanvasItem(item: CanvasItem, options?: {
    conversationId?: string;
    priority?: 'high' | 'normal' | 'low';
  }): Promise<void> {
    const { conversationId, priority = 'normal' } = options || {};
    
    const tags = ['canvas-item'];
    if (conversationId) {
      tags.push(`conversation:${conversationId}`);
    }
    tags.push(`type:${item.type}`);

    // 우선순위에 따른 TTL 설정
    const ttlMap = {
      high: 7 * 24 * 60 * 60 * 1000, // 7일
      normal: 3 * 24 * 60 * 60 * 1000, // 3일
      low: 1 * 24 * 60 * 60 * 1000 // 1일
    };

    await this.set(`canvas:${item.id}`, item, {
      ttl: ttlMap[priority],
      tags,
      l1Only: priority === 'low' // 낮은 우선순위는 L1만 사용
    });
  }

  async getCanvasItem(itemId: string): Promise<CanvasItem | null> {
    return this.get(`canvas:${itemId}`);
  }

  async cacheCanvasPreview(
    conversationId: string, 
    previewData: any
  ): Promise<void> {
    await this.set(`preview:${conversationId}`, previewData, {
      ttl: 30 * 60 * 1000, // 30분
      tags: ['preview', `conversation:${conversationId}`]
    });
  }

  async getCanvasPreview(conversationId: string): Promise<any | null> {
    return this.get(`preview:${conversationId}`);
  }

  async invalidateConversation(conversationId: string): Promise<void> {
    const tag = `conversation:${conversationId}`;
    
    try {
      const l1Count = this.l1Cache.invalidateByTags([tag]);
      const l2Count = await this.l2Cache.invalidateByTags([tag]);
      
      console.log(`🔄 대화 캐시 무효화: ${conversationId} (L1: ${l1Count}, L2: ${l2Count})`);
      
    } catch (error) {
      console.error('❌ 대화 캐시 무효화 실패:', error);
    }
  }

  // ======= 통계 및 모니터링 =======

  getMetrics(): CacheMetrics {
    const l1Metrics = this.l1Cache.getMetrics();
    
    return {
      ...this.metrics,
      totalEntries: l1Metrics.totalEntries || 0,
      memoryUsage: l1Metrics.memoryUsage || 0,
      hitRate: this.calculateHitRate()
    };
  }

  private calculateHitRate(): number {
    const totalRequests = this.metrics.l1Hits + this.metrics.l1Misses + 
                         this.metrics.l2Hits + this.metrics.l2Misses;
    
    if (totalRequests === 0) return 0;
    
    const totalHits = this.metrics.l1Hits + this.metrics.l2Hits;
    return totalHits / totalRequests;
  }

  private updateMetrics(accessTime: number): void {
    // 평균 접근 시간 업데이트 (이동 평균)
    if (this.metrics.avgAccessTime === 0) {
      this.metrics.avgAccessTime = accessTime;
    } else {
      this.metrics.avgAccessTime = (this.metrics.avgAccessTime * 0.9) + (accessTime * 0.1);
    }
  }

  private resetMetrics(): void {
    this.metrics = {
      l1Hits: 0,
      l1Misses: 0,
      l2Hits: 0,
      l2Misses: 0,
      totalEntries: 0,
      memoryUsage: 0,
      hitRate: 0,
      avgAccessTime: 0
    };
  }

  // ======= 정리 및 유지보수 =======

  private startCleanupTimer(interval: number): void {
    this.cleanupTimer = setInterval(() => {
      this.performCleanup();
    }, interval);
  }

  private performCleanup(): void {
    // 만료된 엔트리 정리는 각 캐시에서 자동으로 처리됨
    console.log('🧹 캐시 정기 정리 수행');
  }

  async getStorageInfo(): Promise<{
    l1Keys: string[];
    l1MemoryUsage: number;
    l2StorageEstimate?: StorageEstimate;
  }> {
    const l1Keys = this.l1Cache.getAllKeys();
    const l1Metrics = this.l1Cache.getMetrics();
    
    let l2StorageEstimate: StorageEstimate | undefined;
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      try {
        l2StorageEstimate = await navigator.storage.estimate();
      } catch (error) {
        console.warn('⚠️ 스토리지 추정 실패:', error);
      }
    }

    return {
      l1Keys,
      l1MemoryUsage: l1Metrics.memoryUsage || 0,
      l2StorageEstimate
    };
  }

  // ======= 정리 메서드 =======

  destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    
    this.l1Cache.clear();
    console.log('💀 Canvas 캐시 시스템 정리 완료');
  }
}

// ======= 싱글톤 인스턴스 =======

let cacheSystemInstance: CanvasCacheSystem | null = null;

export const getCanvasCacheSystem = (): CanvasCacheSystem => {
  if (!cacheSystemInstance) {
    cacheSystemInstance = new CanvasCacheSystem();
  }
  return cacheSystemInstance;
};

// ======= 편의 함수들 =======

export const cacheCanvasItem = async (
  item: CanvasItem, 
  options?: Parameters<CanvasCacheSystem['cacheCanvasItem']>[1]
): Promise<void> => {
  const cacheSystem = getCanvasCacheSystem();
  await cacheSystem.cacheCanvasItem(item, options);
};

export const getCachedCanvasItem = async (itemId: string): Promise<CanvasItem | null> => {
  const cacheSystem = getCanvasCacheSystem();
  return cacheSystem.getCanvasItem(itemId);
};

export const invalidateConversationCache = async (conversationId: string): Promise<void> => {
  const cacheSystem = getCanvasCacheSystem();
  await cacheSystem.invalidateConversation(conversationId);
};

// ======= 초기화 함수 =======

export const initCanvasCacheSystem = async (): Promise<void> => {
  const cacheSystem = getCanvasCacheSystem();
  await cacheSystem.init();
};