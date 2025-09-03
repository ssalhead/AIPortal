// Template Store
// AIPortal Canvas Template Library - 템플릿 상태 관리 스토어

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

import {
  TemplateResponse,
  TemplateDetailResponse,
  TemplateSearchRequest,
  TemplateSearchResponse,
  TemplateCreateRequest,
  TemplateUpdateRequest,
  TemplateApplyRequest,
  TemplateCustomizationRequest,
  TemplateReviewRequest,
  CollectionResponse,
  CustomizationPresetResponse,
  TemplateAnalyticsResponse,
  TagResponse
} from '../types/template';

import { templateService } from '../services/templateService';

// ===== 스토어 인터페이스 =====

interface TemplateState {
  // Basic state
  templates: TemplateResponse[];
  featuredTemplates: TemplateResponse[];
  trendingTemplates: TemplateResponse[];
  searchResults: TemplateSearchResponse | null;
  currentTemplate: TemplateDetailResponse | null;
  
  // User data
  favorites: TemplateResponse[];
  collections: CollectionResponse[];
  myTemplates: TemplateResponse[];
  
  // Metadata
  categories: any[];
  popularTags: string[];
  tagSuggestions: any[];
  
  // Loading states
  loading: boolean;
  searchLoading: boolean;
  templateLoading: boolean;
  favoriteLoading: boolean;
  
  // Error states
  error: string | null;
  searchError: string | null;
  templateError: string | null;
  
  // Cache
  cache: Map<string, { data: any; timestamp: number; ttl: number }>;
  
  // Actions
  searchTemplates: (request: TemplateSearchRequest) => Promise<void>;
  getFeaturedTemplates: (limit?: number) => Promise<void>;
  getTrendingTemplates: (limit?: number, days?: number) => Promise<void>;
  getTemplate: (id: string) => Promise<TemplateDetailResponse | null>;
  createTemplate: (request: TemplateCreateRequest) => Promise<TemplateDetailResponse>;
  updateTemplate: (id: string, request: TemplateUpdateRequest) => Promise<TemplateDetailResponse>;
  deleteTemplate: (id: string) => Promise<void>;
  
  // Template operations
  applyTemplate: (id: string, request: TemplateApplyRequest) => Promise<any>;
  customizeTemplate: (id: string, request: TemplateCustomizationRequest) => Promise<any>;
  
  // Favorites
  toggleFavorite: (id: string) => Promise<void>;
  getFavorites: (page?: number, pageSize?: number) => Promise<void>;
  
  // Reviews
  addReview: (id: string, review: TemplateReviewRequest) => Promise<void>;
  
  // Collections
  createCollection: (name: string, description?: string) => Promise<void>;
  addToCollection: (collectionId: string, templateId: string) => Promise<void>;
  
  // Metadata
  getCategories: () => Promise<void>;
  getPopularTags: (limit?: number) => Promise<string[]>;
  getTagSuggestions: (query: string, category?: string, limit?: number) => Promise<any[]>;
  getTrendingTags: (days?: number, limit?: number) => Promise<any[]>;
  
  // Template metadata extraction
  extractTemplateMetadata: (name: string, description?: string, canvasData?: any) => Promise<any>;
  
  // Cache operations
  getCachedData: <T>(key: string) => T | null;
  setCachedData: <T>(key: string, data: T, ttl?: number) => void;
  clearCache: () => void;
  
  // Utility actions
  clearError: () => void;
  clearSearchResults: () => void;
  reset: () => void;
}

// ===== 기본 상태 =====

const initialState = {
  // Basic state
  templates: [],
  featuredTemplates: [],
  trendingTemplates: [],
  searchResults: null,
  currentTemplate: null,
  
  // User data
  favorites: [],
  collections: [],
  myTemplates: [],
  
  // Metadata
  categories: [],
  popularTags: [],
  tagSuggestions: [],
  
  // Loading states
  loading: false,
  searchLoading: false,
  templateLoading: false,
  favoriteLoading: false,
  
  // Error states
  error: null,
  searchError: null,
  templateError: null,
  
  // Cache
  cache: new Map<string, { data: any; timestamp: number; ttl: number }>()
};

// ===== 스토어 생성 =====

export const useTemplateStore = create<TemplateState>()(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({
        ...initialState,
        
        // ===== 검색 및 브라우징 =====
        
        searchTemplates: async (request: TemplateSearchRequest) => {
          set((state) => {
            state.searchLoading = true;
            state.searchError = null;
          });

          try {
            // Check cache first
            const cacheKey = `search_${JSON.stringify(request)}`;
            const cached = get().getCachedData<TemplateSearchResponse>(cacheKey);
            
            if (cached) {
              set((state) => {
                state.searchResults = cached;
                state.searchLoading = false;
              });
              return;
            }

            const response = await templateService.searchTemplates(request);
            
            set((state) => {
              state.searchResults = response;
              state.searchLoading = false;
            });

            // Cache the results
            get().setCachedData(cacheKey, response, 5 * 60 * 1000); // 5 minutes

          } catch (error: any) {
            set((state) => {
              state.searchError = error.message || 'Search failed';
              state.searchLoading = false;
            });
          }
        },

        getFeaturedTemplates: async (limit = 20) => {
          set((state) => {
            state.loading = true;
            state.error = null;
          });

          try {
            const cacheKey = `featured_${limit}`;
            const cached = get().getCachedData<TemplateResponse[]>(cacheKey);
            
            if (cached) {
              set((state) => {
                state.featuredTemplates = cached;
                state.loading = false;
              });
              return;
            }

            const response = await templateService.getFeaturedTemplates(limit);
            
            set((state) => {
              state.featuredTemplates = response;
              state.loading = false;
            });

            get().setCachedData(cacheKey, response, 10 * 60 * 1000); // 10 minutes

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to load featured templates';
              state.loading = false;
            });
          }
        },

        getTrendingTemplates: async (limit = 20, days = 7) => {
          set((state) => {
            state.loading = true;
            state.error = null;
          });

          try {
            const cacheKey = `trending_${limit}_${days}`;
            const cached = get().getCachedData<TemplateResponse[]>(cacheKey);
            
            if (cached) {
              set((state) => {
                state.trendingTemplates = cached;
                state.loading = false;
              });
              return;
            }

            const response = await templateService.getTrendingTemplates(limit, days);
            
            set((state) => {
              state.trendingTemplates = response;
              state.loading = false;
            });

            get().setCachedData(cacheKey, response, 15 * 60 * 1000); // 15 minutes

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to load trending templates';
              state.loading = false;
            });
          }
        },

        // ===== 템플릿 상세 조회 =====
        
        getTemplate: async (id: string) => {
          set((state) => {
            state.templateLoading = true;
            state.templateError = null;
          });

          try {
            const cacheKey = `template_${id}`;
            const cached = get().getCachedData<TemplateDetailResponse>(cacheKey);
            
            if (cached) {
              set((state) => {
                state.currentTemplate = cached;
                state.templateLoading = false;
              });
              return cached;
            }

            const response = await templateService.getTemplate(id);
            
            set((state) => {
              state.currentTemplate = response;
              state.templateLoading = false;
            });

            get().setCachedData(cacheKey, response, 30 * 60 * 1000); // 30 minutes
            return response;

          } catch (error: any) {
            set((state) => {
              state.templateError = error.message || 'Failed to load template';
              state.templateLoading = false;
              state.currentTemplate = null;
            });
            return null;
          }
        },

        // ===== 템플릿 CRUD =====

        createTemplate: async (request: TemplateCreateRequest) => {
          set((state) => {
            state.loading = true;
            state.error = null;
          });

          try {
            const response = await templateService.createTemplate(request);
            
            set((state) => {
              state.myTemplates.unshift(response);
              state.loading = false;
            });

            // Clear relevant caches
            get().clearCache();
            
            return response;

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to create template';
              state.loading = false;
            });
            throw error;
          }
        },

        updateTemplate: async (id: string, request: TemplateUpdateRequest) => {
          set((state) => {
            state.loading = true;
            state.error = null;
          });

          try {
            const response = await templateService.updateTemplate(id, request);
            
            set((state) => {
              // Update in various lists
              const updateTemplate = (list: TemplateResponse[]) => {
                const index = list.findIndex(t => t.id === id);
                if (index !== -1) {
                  list[index] = response;
                }
              };
              
              updateTemplate(state.myTemplates);
              updateTemplate(state.templates);
              updateTemplate(state.featuredTemplates);
              updateTemplate(state.trendingTemplates);
              updateTemplate(state.favorites);
              
              if (state.currentTemplate && state.currentTemplate.id === id) {
                state.currentTemplate = response;
              }
              
              if (state.searchResults) {
                updateTemplate(state.searchResults.templates);
              }
              
              state.loading = false;
            });

            // Clear template cache
            get().setCachedData(`template_${id}`, null);
            
            return response;

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to update template';
              state.loading = false;
            });
            throw error;
          }
        },

        deleteTemplate: async (id: string) => {
          set((state) => {
            state.loading = true;
            state.error = null;
          });

          try {
            await templateService.deleteTemplate(id);
            
            set((state) => {
              // Remove from various lists
              const removeTemplate = (list: TemplateResponse[]) => {
                const index = list.findIndex(t => t.id === id);
                if (index !== -1) {
                  list.splice(index, 1);
                }
              };
              
              removeTemplate(state.myTemplates);
              removeTemplate(state.templates);
              removeTemplate(state.featuredTemplates);
              removeTemplate(state.trendingTemplates);
              removeTemplate(state.favorites);
              
              if (state.searchResults) {
                removeTemplate(state.searchResults.templates);
                state.searchResults.total = Math.max(0, state.searchResults.total - 1);
              }
              
              if (state.currentTemplate && state.currentTemplate.id === id) {
                state.currentTemplate = null;
              }
              
              state.loading = false;
            });

            // Clear template cache
            get().setCachedData(`template_${id}`, null);

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to delete template';
              state.loading = false;
            });
            throw error;
          }
        },

        // ===== 템플릿 적용 및 커스터마이징 =====

        applyTemplate: async (id: string, request: TemplateApplyRequest) => {
          try {
            const response = await templateService.applyTemplate(id, request);
            
            // Track usage
            set((state) => {
              const updateUsage = (list: TemplateResponse[]) => {
                const template = list.find(t => t.id === id);
                if (template) {
                  template.stats.usage_count += 1;
                }
              };
              
              updateUsage(state.templates);
              updateUsage(state.featuredTemplates);
              updateUsage(state.trendingTemplates);
              updateUsage(state.favorites);
              
              if (state.searchResults) {
                updateUsage(state.searchResults.templates);
              }
            });
            
            return response;

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to apply template';
            });
            throw error;
          }
        },

        customizeTemplate: async (id: string, request: TemplateCustomizationRequest) => {
          try {
            const response = await templateService.customizeTemplate(id, request);
            return response;

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to customize template';
            });
            throw error;
          }
        },

        // ===== 즐겨찾기 =====

        toggleFavorite: async (id: string) => {
          set((state) => {
            state.favoriteLoading = true;
          });

          try {
            const response = await templateService.toggleFavorite(id);
            const isFavorite = response.is_favorite;
            
            set((state) => {
              // Update favorite status in all lists
              const updateFavoriteStatus = (list: TemplateResponse[]) => {
                const template = list.find(t => t.id === id);
                if (template) {
                  // Add/remove favorite property (this would need to be added to the type)
                  (template as any).is_favorite = isFavorite;
                }
              };
              
              updateFavoriteStatus(state.templates);
              updateFavoriteStatus(state.featuredTemplates);
              updateFavoriteStatus(state.trendingTemplates);
              
              if (state.searchResults) {
                updateFavoriteStatus(state.searchResults.templates);
              }
              
              // Update favorites list
              if (isFavorite) {
                const template = state.templates.find(t => t.id === id) ||
                               state.featuredTemplates.find(t => t.id === id) ||
                               state.trendingTemplates.find(t => t.id === id);
                if (template && !state.favorites.find(f => f.id === id)) {
                  state.favorites.unshift(template);
                }
              } else {
                const index = state.favorites.findIndex(f => f.id === id);
                if (index !== -1) {
                  state.favorites.splice(index, 1);
                }
              }
              
              state.favoriteLoading = false;
            });

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to toggle favorite';
              state.favoriteLoading = false;
            });
          }
        },

        getFavorites: async (page = 1, pageSize = 20) => {
          set((state) => {
            state.favoriteLoading = true;
            state.error = null;
          });

          try {
            const response = await templateService.getFavorites(page, pageSize);
            
            set((state) => {
              if (page === 1) {
                state.favorites = response.templates;
              } else {
                state.favorites.push(...response.templates);
              }
              state.favoriteLoading = false;
            });

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to load favorites';
              state.favoriteLoading = false;
            });
          }
        },

        // ===== 리뷰 =====

        addReview: async (id: string, review: TemplateReviewRequest) => {
          try {
            await templateService.addReview(id, review);
            
            // Update template rating (optimistic update)
            set((state) => {
              const updateRating = (list: TemplateResponse[]) => {
                const template = list.find(t => t.id === id);
                if (template) {
                  // This is a simplified calculation
                  const newCount = template.stats.rating_count + 1;
                  const newAverage = (template.stats.average_rating * template.stats.rating_count + review.rating) / newCount;
                  template.stats.average_rating = Number(newAverage.toFixed(1));
                  template.stats.rating_count = newCount;
                }
              };
              
              updateRating(state.templates);
              updateRating(state.featuredTemplates);
              updateRating(state.trendingTemplates);
              updateRating(state.favorites);
              
              if (state.searchResults) {
                updateRating(state.searchResults.templates);
              }
            });
            
            // Clear template cache to refresh reviews
            get().setCachedData(`template_${id}`, null);

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to add review';
            });
          }
        },

        // ===== 컬렉션 =====

        createCollection: async (name: string, description?: string) => {
          try {
            const response = await templateService.createCollection(name, description);
            
            set((state) => {
              state.collections.unshift(response);
            });

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to create collection';
            });
          }
        },

        addToCollection: async (collectionId: string, templateId: string) => {
          try {
            await templateService.addToCollection(collectionId, templateId);
            
            set((state) => {
              const collection = state.collections.find(c => c.id === collectionId);
              if (collection) {
                collection.template_count += 1;
              }
            });

          } catch (error: any) {
            set((state) => {
              state.error = error.message || 'Failed to add to collection';
            });
          }
        },

        // ===== 메타데이터 =====

        getCategories: async () => {
          try {
            const cacheKey = 'categories';
            const cached = get().getCachedData<any[]>(cacheKey);
            
            if (cached) {
              set((state) => {
                state.categories = cached;
              });
              return;
            }

            const response = await templateService.getCategories();
            
            set((state) => {
              state.categories = response;
            });

            get().setCachedData(cacheKey, response, 60 * 60 * 1000); // 1 hour

          } catch (error: any) {
            console.error('Failed to load categories:', error);
          }
        },

        getPopularTags: async (limit = 50) => {
          try {
            const cacheKey = `popular_tags_${limit}`;
            const cached = get().getCachedData<string[]>(cacheKey);
            
            if (cached) {
              set((state) => {
                state.popularTags = cached;
              });
              return cached;
            }

            const response = await templateService.getPopularTags(limit);
            
            set((state) => {
              state.popularTags = response;
            });

            get().setCachedData(cacheKey, response, 30 * 60 * 1000); // 30 minutes
            return response;

          } catch (error: any) {
            console.error('Failed to load popular tags:', error);
            return [];
          }
        },

        getTagSuggestions: async (query: string, category?: string, limit = 10) => {
          try {
            const response = await templateService.getTagSuggestions(query, category, limit);
            
            set((state) => {
              state.tagSuggestions = response;
            });

            return response;

          } catch (error: any) {
            console.error('Failed to get tag suggestions:', error);
            return [];
          }
        },

        getTrendingTags: async (days = 7, limit = 20) => {
          try {
            const cacheKey = `trending_tags_${days}_${limit}`;
            const cached = get().getCachedData<any[]>(cacheKey);
            
            if (cached) return cached;

            const response = await templateService.getTrendingTags(days, limit);
            
            get().setCachedData(cacheKey, response, 15 * 60 * 1000); // 15 minutes
            return response;

          } catch (error: any) {
            console.error('Failed to get trending tags:', error);
            return [];
          }
        },

        // ===== 템플릿 메타데이터 추출 =====

        extractTemplateMetadata: async (name: string, description?: string, canvasData?: any) => {
          try {
            // This would call the metadata service
            const response = await templateService.extractMetadata(name, description, canvasData);
            return response;

          } catch (error: any) {
            console.error('Failed to extract metadata:', error);
            return {};
          }
        },

        // ===== 캐시 관리 =====

        getCachedData: <T>(key: string): T | null => {
          const cache = get().cache;
          const entry = cache.get(key);
          
          if (!entry) return null;
          
          // Check if expired
          if (Date.now() > entry.timestamp + entry.ttl) {
            cache.delete(key);
            return null;
          }
          
          return entry.data as T;
        },

        setCachedData: <T>(key: string, data: T, ttl = 5 * 60 * 1000) => {
          if (data === null) {
            get().cache.delete(key);
            return;
          }
          
          set((state) => {
            state.cache.set(key, {
              data,
              timestamp: Date.now(),
              ttl
            });
          });
        },

        clearCache: () => {
          set((state) => {
            state.cache.clear();
          });
        },

        // ===== 유틸리티 =====

        clearError: () => {
          set((state) => {
            state.error = null;
            state.searchError = null;
            state.templateError = null;
          });
        },

        clearSearchResults: () => {
          set((state) => {
            state.searchResults = null;
            state.searchError = null;
          });
        },

        reset: () => {
          set(initialState);
        }
      }))
    ),
    {
      name: 'template-store',
      partialize: (state) => ({
        // Only persist user-specific data
        favorites: state.favorites,
        collections: state.collections,
        myTemplates: state.myTemplates,
        popularTags: state.popularTags
      })
    }
  )
);

// ===== 스토어 구독 및 사이드 이펙트 =====

// Auto-clear errors after 5 seconds
useTemplateStore.subscribe(
  (state) => state.error,
  (error) => {
    if (error) {
      setTimeout(() => {
        useTemplateStore.getState().clearError();
      }, 5000);
    }
  }
);

// Log state changes in development
if (process.env.NODE_ENV === 'development') {
  useTemplateStore.subscribe((state) => {
    console.log('Template store state changed:', {
      templatesCount: state.templates.length,
      featuredCount: state.featuredTemplates.length,
      trendingCount: state.trendingTemplates.length,
      favoritesCount: state.favorites.length,
      loading: state.loading,
      error: state.error
    });
  });
}

export default useTemplateStore;