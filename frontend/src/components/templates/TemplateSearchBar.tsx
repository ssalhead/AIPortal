// Template Search Bar Component
// AIPortal Canvas Template Library - 템플릿 검색 바 컴포넌트

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, X, Clock, TrendingUp, Star, Tag, 
  Hash, Sparkles, Filter, ChevronDown
} from 'lucide-react';

import { cn } from '../../utils/cn';
import { useDebounce } from '../../hooks/useDebounce';
import { useTemplateStore } from '../../stores/templateStore';

interface SearchSuggestion {
  type: 'query' | 'tag' | 'category' | 'recent' | 'trending';
  value: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

interface TemplateSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  showSuggestions?: boolean;
  showQuickFilters?: boolean;
  onTagSelect?: (tag: string) => void;
  onCategorySelect?: (category: string) => void;
}

const TemplateSearchBar: React.FC<TemplateSearchBarProps> = ({
  value,
  onChange,
  placeholder = '템플릿, 태그, 카테고리 검색...',
  className,
  showSuggestions = true,
  showQuickFilters = false,
  onTagSelect,
  onCategorySelect
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedValue = useDebounce(value, 200);

  const { getTagSuggestions, getTrendingTags } = useTemplateStore();

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('template-recent-searches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse recent searches:', e);
      }
    }
  }, []);

  // Save search to recent searches
  const saveToRecentSearches = useCallback((query: string) => {
    if (!query.trim() || query.length < 2) return;

    const updated = [query, ...recentSearches.filter(s => s !== query)].slice(0, 10);
    setRecentSearches(updated);
    localStorage.setItem('template-recent-searches', JSON.stringify(updated));
  }, [recentSearches]);

  // Generate suggestions based on input
  const generateSuggestions = useCallback(async (query: string) => {
    const suggestions: SearchSuggestion[] = [];

    if (!query.trim()) {
      // Show recent searches and trending when empty
      recentSearches.slice(0, 5).forEach(search => {
        suggestions.push({
          type: 'recent',
          value: search,
          label: search,
          icon: <Clock className=\"w-4 h-4 text-gray-400\" />
        });
      });

      // Add trending tags
      try {
        const trending = await getTrendingTags(5);
        trending.forEach(tag => {
          suggestions.push({
            type: 'trending',
            value: tag.name,
            label: tag.name,
            count: tag.recent_usage,
            icon: <TrendingUp className=\"w-4 h-4 text-red-500\" />
          });
        });
      } catch (e) {
        console.error('Failed to get trending tags:', e);
      }
    } else {
      // Search-based suggestions
      try {
        const tagSuggestions = await getTagSuggestions(query, undefined, 8);
        
        tagSuggestions.forEach(suggestion => {
          suggestions.push({
            type: 'tag',
            value: suggestion.name,
            label: suggestion.name,
            count: suggestion.usage_count,
            icon: <Tag className=\"w-4 h-4 text-purple-500\" />
          });
        });

        // Add direct query suggestion
        suggestions.unshift({
          type: 'query',
          value: query,
          label: `\"${query}\" 검색`,
          icon: <Search className=\"w-4 h-4 text-blue-500\" />
        });

      } catch (e) {
        console.error('Failed to get suggestions:', e);
        
        // Fallback: just add query suggestion
        suggestions.push({
          type: 'query',
          value: query,
          label: `\"${query}\" 검색`,
          icon: <Search className=\"w-4 h-4 text-blue-500\" />
        });
      }
    }

    setSuggestions(suggestions);
  }, [recentSearches, getTrendingTags, getTagSuggestions]);

  // Update suggestions when search value changes
  useEffect(() => {
    if (showDropdown && showSuggestions) {
      generateSuggestions(debouncedValue);
    }
  }, [debouncedValue, showDropdown, showSuggestions, generateSuggestions]);

  // Handle input focus
  const handleFocus = useCallback(() => {
    setIsFocused(true);
    setShowDropdown(true);
    if (showSuggestions) {
      generateSuggestions(value);
    }
  }, [value, showSuggestions, generateSuggestions]);

  // Handle input blur
  const handleBlur = useCallback(() => {
    // Delay to allow click on suggestion
    setTimeout(() => {
      setIsFocused(false);
      setShowDropdown(false);
      setSelectedIndex(-1);
    }, 150);
  }, []);

  // Handle input change
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    setSelectedIndex(-1);
  }, [onChange]);

  // Handle suggestion selection
  const handleSuggestionSelect = useCallback((suggestion: SearchSuggestion) => {
    const newValue = suggestion.value;
    
    if (suggestion.type === 'tag' && onTagSelect) {
      onTagSelect(newValue);
    } else if (suggestion.type === 'category' && onCategorySelect) {
      onCategorySelect(newValue);
    } else {
      onChange(newValue);
      saveToRecentSearches(newValue);
    }

    setShowDropdown(false);
    setSelectedIndex(-1);
    inputRef.current?.blur();
  }, [onChange, onTagSelect, onCategorySelect, saveToRecentSearches]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!showDropdown || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;

      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;

      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleSuggestionSelect(suggestions[selectedIndex]);
        } else if (value.trim()) {
          saveToRecentSearches(value);
          setShowDropdown(false);
        }
        break;

      case 'Escape':
        setShowDropdown(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  }, [showDropdown, suggestions, selectedIndex, value, handleSuggestionSelect, saveToRecentSearches]);

  // Handle clear
  const handleClear = useCallback(() => {
    onChange('');
    inputRef.current?.focus();
  }, [onChange]);

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={searchRef} className={cn('relative', className)}>
      {/* Search Input */}
      <div className={cn(
        'relative flex items-center border rounded-lg bg-white transition-all duration-200',
        isFocused
          ? 'border-blue-300 ring-2 ring-blue-100 shadow-sm'
          : 'border-gray-300 hover:border-gray-400'
      )}>
        <Search className=\"w-5 h-5 text-gray-400 ml-3 flex-shrink-0\" />
        
        <input
          ref={inputRef}
          type=\"text\"
          value={value}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={cn(
            'flex-1 px-3 py-2.5 bg-transparent border-none outline-none text-gray-900',
            'placeholder:text-gray-500'
          )}
        />

        {/* Clear Button */}
        {value && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={handleClear}
            className=\"p-1 mr-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors\"
          >
            <X className=\"w-4 h-4\" />
          </motion.button>
        )}

        {/* Quick Filters Toggle */}
        {showQuickFilters && (
          <button className=\"flex items-center gap-1 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 border-l border-gray-200 transition-colors\">
            <Filter className=\"w-4 h-4\" />
            필터
            <ChevronDown className=\"w-3 h-3\" />
          </button>
        )}
      </div>

      {/* Suggestions Dropdown */}
      <AnimatePresence>
        {showDropdown && showSuggestions && suggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={cn(
              'absolute top-full left-0 right-0 mt-2 bg-white border border-gray-200',
              'rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto'
            )}
          >
            {/* Recent Searches Header */}
            {!value && recentSearches.length > 0 && (
              <div className=\"px-4 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b border-gray-100\">
                최근 검색
              </div>
            )}

            {/* Trending Header */}
            {!value && suggestions.some(s => s.type === 'trending') && (
              <div className=\"px-4 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b border-gray-100\">
                인기 태그
              </div>
            )}

            {/* Suggestions List */}
            <div className=\"py-1\">
              {suggestions.map((suggestion, index) => (
                <button
                  key={`${suggestion.type}-${suggestion.value}`}
                  onClick={() => handleSuggestionSelect(suggestion)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors',
                    selectedIndex === index
                      ? 'bg-blue-50 text-blue-900'
                      : 'text-gray-700 hover:bg-gray-50'
                  )}
                >
                  {/* Icon */}
                  <div className=\"flex-shrink-0\">
                    {suggestion.icon}
                  </div>

                  {/* Content */}
                  <div className=\"flex-1 min-w-0\">
                    <div className=\"font-medium truncate\">
                      {suggestion.label}
                    </div>
                    {suggestion.type === 'trending' && suggestion.count && (
                      <div className=\"text-xs text-gray-500\">
                        최근 {suggestion.count}회 사용
                      </div>
                    )}
                    {suggestion.type === 'tag' && suggestion.count && (
                      <div className=\"text-xs text-gray-500\">
                        {suggestion.count}개 템플릿
                      </div>
                    )}
                  </div>

                  {/* Type Badge */}
                  {suggestion.type === 'tag' && (
                    <div className=\"flex-shrink-0\">
                      <span className=\"inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800\">
                        태그
                      </span>
                    </div>
                  )}
                  {suggestion.type === 'trending' && (
                    <div className=\"flex-shrink-0\">
                      <span className=\"inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800\">
                        인기
                      </span>
                    </div>
                  )}
                </button>
              ))}
            </div>

            {/* Quick Actions */}
            {value && (
              <div className=\"border-t border-gray-100 p-2\">
                <div className=\"text-xs text-gray-500 mb-2\">빠른 필터</div>
                <div className=\"flex flex-wrap gap-1\">
                  <button
                    onClick={() => onTagSelect?.(value)}
                    className=\"inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-md hover:bg-purple-200 transition-colors\"
                  >
                    <Hash className=\"w-3 h-3\" />
                    태그로 검색
                  </button>
                  <button className=\"inline-flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-md hover:bg-yellow-200 transition-colors\">
                    <Sparkles className=\"w-3 h-3\" />
                    추천만
                  </button>
                  <button className=\"inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs rounded-md hover:bg-green-200 transition-colors\">
                    <Star className=\"w-3 h-3\" />
                    고평점
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default TemplateSearchBar;