// Template Browser Component
// AIPortal Canvas Template Library - 템플릿 브라우저 메인 컴포넌트

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, Filter, Grid3X3, List, Heart, Download, 
  Eye, Star, Tag, Calendar, User, Settings, ChevronDown,
  Sparkles, TrendingUp, Clock, Zap, Palette
} from 'lucide-react';

import {
  TemplateResponse,
  TemplateSearchRequest,
  TemplateSearchResponse,
  TemplateCategory,
  TemplateSubcategory,
  LicenseType,
  DifficultyLevel,
  SortBy,
  TemplateFilters,
  TemplateViewMode,
  CATEGORY_LABELS,
  SUBCATEGORY_LABELS,
  LICENSE_LABELS,
  DIFFICULTY_LABELS
} from '../../types/template';

import { useTemplateStore } from '../../stores/templateStore';
import { useDebounce } from '../../hooks/useDebounce';
import { cn } from '../../utils/cn';

import TemplateCard from './TemplateCard';
import TemplateListItem from './TemplateListItem';
import TemplateFilters from './TemplateFilters';
import TemplateSortPanel from './TemplateSortPanel';
import TemplateSearchBar from './TemplateSearchBar';
import LoadingSpinner from '../ui/LoadingSpinner';
import EmptyState from '../ui/EmptyState';
import Pagination from '../ui/Pagination';

interface TemplateBrowserProps {
  className?: string;
  initialCategory?: TemplateCategory;
  initialSubcategory?: TemplateSubcategory;
  onTemplateSelect?: (template: TemplateResponse) => void;
  onTemplateApply?: (template: TemplateResponse) => void;
  showHeader?: boolean;
  showFilters?: boolean;
  showFeatured?: boolean;
  showTrending?: boolean;
  maxHeight?: string;
}

const TemplateBrowser: React.FC<TemplateBrowserProps> = ({
  className,
  initialCategory,
  initialSubcategory,
  onTemplateSelect,
  onTemplateApply,
  showHeader = true,
  showFilters = true,
  showFeatured = true,
  showTrending = true,
  maxHeight = '800px'
}) => {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<TemplateFilters>({
    category: initialCategory,
    subcategory: initialSubcategory,
    tags: [],
    license_type: undefined,
    difficulty_level: undefined,
    is_featured: undefined,
    min_rating: undefined,
    price_range: undefined,
    date_range: undefined
  });
  const [sortBy, setSortBy] = useState<SortBy>(SortBy.CREATED_DESC);
  const [viewMode, setViewMode] = useState<TemplateViewMode>({
    view: 'grid',
    columns: 3,
    show_preview: true,
    show_details: true
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const [showSortPanel, setShowSortPanel] = useState(false);

  // Hooks
  const debouncedSearchQuery = useDebounce(searchQuery, 300);
  const { 
    templates,
    featuredTemplates,
    trendingTemplates,
    searchResults,
    loading,
    error,
    searchTemplates,
    getFeaturedTemplates,
    getTrendingTemplates,
    toggleFavorite,
    applyTemplate
  } = useTemplateStore();

  // Search request 생성
  const searchRequest = useMemo((): TemplateSearchRequest => ({
    query: debouncedSearchQuery || undefined,
    category: filters.category,
    subcategory: filters.subcategory,
    tags: filters.tags.length > 0 ? filters.tags : undefined,
    license_type: filters.license_type,
    difficulty_level: filters.difficulty_level,
    is_featured: filters.is_featured,
    min_rating: filters.min_rating,
    created_after: filters.date_range?.[0],
    created_before: filters.date_range?.[1],
    sort_by: sortBy,
    page: currentPage,
    page_size: 20
  }), [
    debouncedSearchQuery,
    filters,
    sortBy,
    currentPage
  ]);

  // Effects
  useEffect(() => {
    searchTemplates(searchRequest);
  }, [searchRequest, searchTemplates]);

  useEffect(() => {
    if (showFeatured) {
      getFeaturedTemplates(12);
    }
  }, [showFeatured, getFeaturedTemplates]);

  useEffect(() => {
    if (showTrending) {
      getTrendingTemplates(12, 7);
    }
  }, [showTrending, getTrendingTemplates]);

  // Handlers
  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  }, []);

  const handleFilterChange = useCallback((newFilters: Partial<TemplateFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setCurrentPage(1);
  }, []);

  const handleSortChange = useCallback((newSortBy: SortBy) => {
    setSortBy(newSortBy);
    setCurrentPage(1);
  }, []);

  const handleViewModeChange = useCallback((newViewMode: Partial<TemplateViewMode>) => {
    setViewMode(prev => ({ ...prev, ...newViewMode }));
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handleTemplateClick = useCallback((template: TemplateResponse) => {
    if (onTemplateSelect) {
      onTemplateSelect(template);
    }
  }, [onTemplateSelect]);

  const handleTemplateApply = useCallback(async (template: TemplateResponse) => {
    if (onTemplateApply) {
      onTemplateApply(template);
    }
  }, [onTemplateApply]);

  const handleToggleFavorite = useCallback(async (templateId: string) => {
    await toggleFavorite(templateId);
  }, [toggleFavorite]);

  // 현재 결과 데이터
  const currentResults = searchResults || {
    templates: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0,
    has_next: false,
    has_prev: false
  };

  return (
    <div className={cn('flex flex-col h-full', className)} style={{ maxHeight }}>
      {/* Header */}
      {showHeader && (
        <div className=\"flex-none p-6 border-b border-gray-200 bg-white\">
          <div className=\"flex items-center justify-between mb-4\">
            <div>
              <h1 className=\"text-2xl font-bold text-gray-900\">
                템플릿 라이브러리
              </h1>
              <p className=\"text-gray-600 mt-1\">
                {currentResults.total.toLocaleString()}개의 전문 디자인 템플릿
              </p>
            </div>
            
            <div className=\"flex items-center gap-3\">
              {/* View Mode Toggle */}
              <div className=\"flex items-center gap-1 p-1 bg-gray-100 rounded-lg\">
                <button
                  onClick={() => handleViewModeChange({ view: 'grid' })}
                  className={cn(
                    'p-2 rounded-md transition-colors',
                    viewMode.view === 'grid' 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-500 hover:text-gray-700'
                  )}
                >
                  <Grid3X3 className=\"w-4 h-4\" />
                </button>
                <button
                  onClick={() => handleViewModeChange({ view: 'list' })}
                  className={cn(
                    'p-2 rounded-md transition-colors',
                    viewMode.view === 'list' 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-500 hover:text-gray-700'
                  )}
                >
                  <List className=\"w-4 h-4\" />
                </button>
              </div>

              {/* Sort Button */}
              <div className=\"relative\">
                <button
                  onClick={() => setShowSortPanel(!showSortPanel)}
                  className=\"flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors\"
                >
                  <Settings className=\"w-4 h-4\" />
                  정렬
                  <ChevronDown className=\"w-4 h-4\" />
                </button>
                
                <AnimatePresence>
                  {showSortPanel && (
                    <TemplateSortPanel
                      sortBy={sortBy}
                      onSortChange={handleSortChange}
                      onClose={() => setShowSortPanel(false)}
                    />
                  )}
                </AnimatePresence>
              </div>

              {/* Filters Button */}
              {showFilters && (
                <button
                  onClick={() => setShowFiltersPanel(!showFiltersPanel)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
                    showFiltersPanel || Object.values(filters).some(v => v !== undefined && (Array.isArray(v) ? v.length > 0 : true))
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                  )}
                >
                  <Filter className=\"w-4 h-4\" />
                  필터
                  {Object.values(filters).some(v => v !== undefined && (Array.isArray(v) ? v.length > 0 : true)) && (
                    <span className=\"w-2 h-2 bg-blue-500 rounded-full\" />
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Search Bar */}
          <TemplateSearchBar
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder=\"템플릿 검색...\"
            className=\"mb-4\"
          />

          {/* Quick Filters */}
          <div className=\"flex items-center gap-2 overflow-x-auto pb-2\">
            <button
              onClick={() => handleFilterChange({ is_featured: !filters.is_featured })}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap',
                filters.is_featured
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              <Sparkles className=\"w-4 h-4\" />
              추천
            </button>
            
            {Object.values(TemplateCategory).map((category) => (
              <button
                key={category}
                onClick={() => handleFilterChange({ 
                  category: filters.category === category ? undefined : category,
                  subcategory: undefined
                })}
                className={cn(
                  'px-3 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap',
                  filters.category === category
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                )}
              >
                {CATEGORY_LABELS[category]}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className=\"flex-1 flex min-h-0\">
        {/* Filters Sidebar */}
        <AnimatePresence>
          {showFiltersPanel && showFilters && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 300, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className=\"flex-none border-r border-gray-200 bg-white overflow-hidden\"
            >
              <TemplateFilters
                filters={filters}
                onChange={handleFilterChange}
                onClose={() => setShowFiltersPanel(false)}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main Content */}
        <div className=\"flex-1 overflow-auto\">
          <div className=\"p-6\">
            {/* Featured Templates */}
            {showFeatured && featuredTemplates && featuredTemplates.length > 0 && !debouncedSearchQuery && (
              <div className=\"mb-8\">
                <div className=\"flex items-center gap-2 mb-4\">
                  <Sparkles className=\"w-5 h-5 text-yellow-500\" />
                  <h2 className=\"text-lg font-semibold text-gray-900\">추천 템플릿</h2>
                </div>
                
                <div className=\"grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6\">
                  {featuredTemplates.slice(0, 8).map((template) => (
                    <TemplateCard
                      key={template.id}
                      template={template}
                      onClick={() => handleTemplateClick(template)}
                      onApply={() => handleTemplateApply(template)}
                      onToggleFavorite={() => handleToggleFavorite(template.id)}
                      showPreview={viewMode.show_preview}
                      showDetails={viewMode.show_details}
                      featured
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Trending Templates */}
            {showTrending && trendingTemplates && trendingTemplates.length > 0 && !debouncedSearchQuery && (
              <div className=\"mb-8\">
                <div className=\"flex items-center gap-2 mb-4\">
                  <TrendingUp className=\"w-5 h-5 text-red-500\" />
                  <h2 className=\"text-lg font-semibold text-gray-900\">트렌딩 템플릿</h2>
                </div>
                
                <div className=\"grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6\">
                  {trendingTemplates.slice(0, 8).map((template) => (
                    <TemplateCard
                      key={template.id}
                      template={template}
                      onClick={() => handleTemplateClick(template)}
                      onApply={() => handleTemplateApply(template)}
                      onToggleFavorite={() => handleToggleFavorite(template.id)}
                      showPreview={viewMode.show_preview}
                      showDetails={viewMode.show_details}
                      trending
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Search Results Header */}
            {(debouncedSearchQuery || Object.values(filters).some(v => v !== undefined && (Array.isArray(v) ? v.length > 0 : true))) && (
              <div className=\"flex items-center justify-between mb-4\">
                <div className=\"flex items-center gap-4\">
                  <h2 className=\"text-lg font-semibold text-gray-900\">
                    검색 결과
                  </h2>
                  <span className=\"text-sm text-gray-600\">
                    {currentResults.total.toLocaleString()}개 템플릿
                  </span>
                </div>

                {/* Applied Filters */}
                {Object.entries(filters).some(([key, value]) => 
                  value !== undefined && (Array.isArray(value) ? value.length > 0 : true)
                ) && (
                  <div className=\"flex items-center gap-2\">
                    <span className=\"text-sm text-gray-500\">필터:</span>
                    {filters.category && (
                      <span className=\"inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-md\">
                        {CATEGORY_LABELS[filters.category]}
                        <button
                          onClick={() => handleFilterChange({ category: undefined, subcategory: undefined })}
                          className=\"text-blue-600 hover:text-blue-800\"
                        >
                          ×
                        </button>
                      </span>
                    )}
                    {filters.license_type && (
                      <span className=\"inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-sm rounded-md\">
                        {LICENSE_LABELS[filters.license_type]}
                        <button
                          onClick={() => handleFilterChange({ license_type: undefined })}
                          className=\"text-green-600 hover:text-green-800\"
                        >
                          ×
                        </button>
                      </span>
                    )}
                    {filters.tags.map((tag) => (
                      <span key={tag} className=\"inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-800 text-sm rounded-md\">
                        {tag}
                        <button
                          onClick={() => handleFilterChange({ 
                            tags: filters.tags.filter(t => t !== tag)
                          })}
                          className=\"text-purple-600 hover:text-purple-800\"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Loading State */}
            {loading && (
              <div className=\"flex items-center justify-center py-12\">
                <LoadingSpinner size=\"lg\" />
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div className=\"text-center py-12\">
                <div className=\"text-red-500 mb-2\">오류가 발생했습니다</div>
                <div className=\"text-gray-600 text-sm\">{error}</div>
              </div>
            )}

            {/* Empty State */}
            {!loading && !error && currentResults.templates.length === 0 && (
              <EmptyState
                title=\"템플릿을 찾을 수 없습니다\"
                description=\"검색 조건을 변경하거나 필터를 조정해보세요.\"
                icon={<Search className=\"w-12 h-12 text-gray-400\" />}
              />
            )}

            {/* Templates Grid/List */}
            {!loading && !error && currentResults.templates.length > 0 && (
              <>
                {viewMode.view === 'grid' ? (
                  <div className={cn(
                    'grid gap-4 mb-6',
                    viewMode.columns === 2 && 'grid-cols-1 sm:grid-cols-2',
                    viewMode.columns === 3 && 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
                    viewMode.columns === 4 && 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
                    viewMode.columns === 5 && 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5'
                  )}>
                    {currentResults.templates.map((template) => (
                      <TemplateCard
                        key={template.id}
                        template={template}
                        onClick={() => handleTemplateClick(template)}
                        onApply={() => handleTemplateApply(template)}
                        onToggleFavorite={() => handleToggleFavorite(template.id)}
                        showPreview={viewMode.show_preview}
                        showDetails={viewMode.show_details}
                      />
                    ))}
                  </div>
                ) : (
                  <div className=\"space-y-3 mb-6\">
                    {currentResults.templates.map((template) => (
                      <TemplateListItem
                        key={template.id}
                        template={template}
                        onClick={() => handleTemplateClick(template)}
                        onApply={() => handleTemplateApply(template)}
                        onToggleFavorite={() => handleToggleFavorite(template.id)}
                        showDetails={viewMode.show_details}
                      />
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {currentResults.total_pages > 1 && (
                  <div className=\"flex justify-center\">
                    <Pagination
                      currentPage={currentResults.page}
                      totalPages={currentResults.total_pages}
                      onPageChange={handlePageChange}
                      showPageNumbers
                      showFirstLast
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemplateBrowser;