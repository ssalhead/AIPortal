// Template Filters Component
// AIPortal Canvas Template Library - 템플릿 필터 패널 컴포넌트

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, ChevronDown, ChevronUp, Star, Calendar, 
  Crown, Zap, Palette, Award, Lock, Check,
  Search, Filter, RotateCcw, Sparkles
} from 'lucide-react';

import {
  TemplateFilters as ITemplateFilters,
  TemplateCategory,
  TemplateSubcategory,
  LicenseType,
  DifficultyLevel,
  CATEGORY_LABELS,
  SUBCATEGORY_LABELS,
  LICENSE_LABELS,
  DIFFICULTY_LABELS
} from '../../types/template';

import { cn } from '../../utils/cn';
import { useTemplateStore } from '../../stores/templateStore';
import Button from '../ui/Button';
import Checkbox from '../ui/Checkbox';
import RadioGroup from '../ui/RadioGroup';
import Slider from '../ui/Slider';
import Badge from '../ui/Badge';
import TagInput from '../ui/TagInput';
import DateRangePicker from '../ui/DateRangePicker';

interface TemplateFiltersProps {
  filters: ITemplateFilters;
  onChange: (filters: Partial<ITemplateFilters>) => void;
  onClose?: () => void;
  className?: string;
}

interface FilterSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  expanded: boolean;
}

const TemplateFilters: React.FC<TemplateFiltersProps> = ({
  filters,
  onChange,
  onClose,
  className
}) => {
  const [sections, setSections] = useState<FilterSection[]>([
    { id: 'category', title: '카테고리', icon: <Palette className=\"w-4 h-4\" />, expanded: true },
    { id: 'license', title: '라이선스', icon: <Lock className=\"w-4 h-4\" />, expanded: true },
    { id: 'difficulty', title: '난이도', icon: <Award className=\"w-4 h-4\" />, expanded: false },
    { id: 'rating', title: '평점', icon: <Star className=\"w-4 h-4\" />, expanded: false },
    { id: 'features', title: '특징', icon: <Sparkles className=\"w-4 h-4\" />, expanded: false },
    { id: 'tags', title: '태그', icon: <Zap className=\"w-4 h-4\" />, expanded: false },
    { id: 'date', title: '생성일', icon: <Calendar className=\"w-4 h-4\" />, expanded: false }
  ]);

  const [tagInput, setTagInput] = useState('');
  const [tagSuggestions, setTagSuggestions] = useState<string[]>([]);
  
  const { getPopularTags, getTagSuggestions } = useTemplateStore();

  // Load popular tags on mount
  useEffect(() => {
    const loadPopularTags = async () => {
      try {
        const tags = await getPopularTags(20);
        setTagSuggestions(tags);
      } catch (error) {
        console.error('Failed to load popular tags:', error);
      }
    };

    loadPopularTags();
  }, [getPopularTags]);

  // Toggle section
  const toggleSection = useCallback((sectionId: string) => {
    setSections(prev => prev.map(section => 
      section.id === sectionId 
        ? { ...section, expanded: !section.expanded }
        : section
    ));
  }, []);

  // Reset all filters
  const resetFilters = useCallback(() => {
    onChange({
      category: undefined,
      subcategory: undefined,
      tags: [],
      license_type: undefined,
      difficulty_level: undefined,
      is_featured: undefined,
      min_rating: undefined,
      price_range: undefined,
      date_range: undefined
    });
  }, [onChange]);

  // Check if any filters are active
  const hasActiveFilters = Object.values(filters).some(value => 
    value !== undefined && (Array.isArray(value) ? value.length > 0 : true)
  );

  // Get available subcategories for selected category
  const availableSubcategories = filters.category 
    ? Object.values(TemplateSubcategory).filter(subcat => {
        // Simple matching based on category prefix
        const categoryPrefix = filters.category?.split('_')[0] || '';
        return subcat.startsWith(categoryPrefix) || 
               (filters.category === TemplateCategory.SOCIAL_MEDIA && subcat.includes('post')) ||
               (filters.category === TemplateCategory.BUSINESS && ['business_card', 'brochure', 'flyer', 'presentation', 'invoice', 'letterhead'].includes(subcat)) ||
               (filters.category === TemplateCategory.EDUCATION && ['infographic', 'diagram', 'chart', 'worksheet', 'certificate', 'presentation_slide'].includes(subcat)) ||
               (filters.category === TemplateCategory.EVENT && ['poster', 'ticket', 'invitation', 'banner', 'program', 'badge'].includes(subcat)) ||
               (filters.category === TemplateCategory.PERSONAL && ['birthday', 'wedding', 'travel', 'hobby', 'family', 'anniversary'].includes(subcat));
      })
    : [];

  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* Header */}
      <div className=\"flex-none p-4 border-b border-gray-200\">
        <div className=\"flex items-center justify-between mb-3\">
          <div className=\"flex items-center gap-2\">
            <Filter className=\"w-5 h-5 text-gray-600\" />
            <h3 className=\"font-semibold text-gray-900\">필터</h3>
            {hasActiveFilters && (
              <Badge variant=\"primary\" size=\"sm\">
                {Object.values(filters).filter(v => 
                  v !== undefined && (Array.isArray(v) ? v.length > 0 : true)
                ).length}
              </Badge>
            )}
          </div>
          
          <div className=\"flex items-center gap-2\">
            {hasActiveFilters && (
              <Button
                variant=\"ghost\"
                size=\"sm\"
                onClick={resetFilters}
                className=\"text-gray-500 hover:text-gray-700\"
              >
                <RotateCcw className=\"w-4 h-4 mr-1\" />
                초기화
              </Button>
            )}
            
            {onClose && (
              <Button
                variant=\"ghost\"
                size=\"sm\"
                onClick={onClose}
                className=\"text-gray-500 hover:text-gray-700\"
              >
                <X className=\"w-4 h-4\" />
              </Button>
            )}
          </div>
        </div>

        {/* Active Filters */}
        {hasActiveFilters && (
          <div className=\"space-y-2\">
            <div className=\"text-xs font-medium text-gray-500 mb-2\">적용된 필터</div>
            <div className=\"flex flex-wrap gap-1\">
              {filters.category && (
                <Badge
                  variant=\"secondary\"
                  size=\"sm\"
                  className=\"flex items-center gap-1\"
                >
                  {CATEGORY_LABELS[filters.category]}
                  <button
                    onClick={() => onChange({ category: undefined, subcategory: undefined })}
                    className=\"text-gray-500 hover:text-gray-700\"
                  >
                    <X className=\"w-3 h-3\" />
                  </button>
                </Badge>
              )}
              
              {filters.subcategory && (
                <Badge
                  variant=\"secondary\"
                  size=\"sm\"
                  className=\"flex items-center gap-1\"
                >
                  {SUBCATEGORY_LABELS[filters.subcategory]}
                  <button
                    onClick={() => onChange({ subcategory: undefined })}
                    className=\"text-gray-500 hover:text-gray-700\"
                  >
                    <X className=\"w-3 h-3\" />
                  </button>
                </Badge>
              )}
              
              {filters.license_type && (
                <Badge
                  variant=\"secondary\"
                  size=\"sm\"
                  className=\"flex items-center gap-1\"
                >
                  {LICENSE_LABELS[filters.license_type]}
                  <button
                    onClick={() => onChange({ license_type: undefined })}
                    className=\"text-gray-500 hover:text-gray-700\"
                  >
                    <X className=\"w-3 h-3\" />
                  </button>
                </Badge>
              )}
              
              {filters.difficulty_level && (
                <Badge
                  variant=\"secondary\"
                  size=\"sm\"
                  className=\"flex items-center gap-1\"
                >
                  {DIFFICULTY_LABELS[filters.difficulty_level]}
                  <button
                    onClick={() => onChange({ difficulty_level: undefined })}
                    className=\"text-gray-500 hover:text-gray-700\"
                  >
                    <X className=\"w-3 h-3\" />
                  </button>
                </Badge>
              )}
              
              {filters.is_featured && (
                <Badge
                  variant=\"warning\"
                  size=\"sm\"
                  className=\"flex items-center gap-1\"
                >
                  <Crown className=\"w-3 h-3\" />
                  추천
                  <button
                    onClick={() => onChange({ is_featured: undefined })}
                    className=\"text-yellow-700 hover:text-yellow-900\"
                  >
                    <X className=\"w-3 h-3\" />
                  </button>
                </Badge>
              )}
              
              {filters.tags.map((tag) => (
                <Badge
                  key={tag}
                  variant=\"secondary\"
                  size=\"sm\"
                  className=\"flex items-center gap-1\"
                >
                  #{tag}
                  <button
                    onClick={() => onChange({ 
                      tags: filters.tags.filter(t => t !== tag)
                    })}
                    className=\"text-gray-500 hover:text-gray-700\"
                  >
                    <X className=\"w-3 h-3\" />
                  </button>
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filter Sections */}
      <div className=\"flex-1 overflow-y-auto\">
        <div className=\"p-4 space-y-4\">
          {sections.map((section) => (
            <div key={section.id} className=\"border border-gray-200 rounded-lg overflow-hidden\">
              <button
                onClick={() => toggleSection(section.id)}
                className=\"w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors\"
              >
                <div className=\"flex items-center gap-2\">
                  {section.icon}
                  <span className=\"font-medium text-gray-900\">{section.title}</span>
                </div>
                {section.expanded ? (
                  <ChevronUp className=\"w-4 h-4 text-gray-500\" />
                ) : (
                  <ChevronDown className=\"w-4 h-4 text-gray-500\" />
                )}
              </button>
              
              <AnimatePresence>
                {section.expanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className=\"overflow-hidden\"
                  >
                    <div className=\"p-4 border-t border-gray-200\">
                      {section.id === 'category' && (
                        <div className=\"space-y-4\">
                          {/* Category Selection */}
                          <div>
                            <div className=\"text-sm font-medium text-gray-700 mb-2\">카테고리</div>
                            <div className=\"space-y-2\">
                              {Object.values(TemplateCategory).map((category) => (
                                <label key={category} className=\"flex items-center space-x-2 cursor-pointer\">
                                  <input
                                    type=\"radio\"
                                    name=\"category\"
                                    checked={filters.category === category}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        onChange({ category, subcategory: undefined });
                                      }
                                    }}
                                    className=\"text-blue-600\"
                                  />
                                  <span className=\"text-sm text-gray-700\">
                                    {CATEGORY_LABELS[category]}
                                  </span>
                                </label>
                              ))}
                              <label className=\"flex items-center space-x-2 cursor-pointer\">
                                <input
                                  type=\"radio\"
                                  name=\"category\"
                                  checked={!filters.category}
                                  onChange={() => onChange({ category: undefined, subcategory: undefined })}
                                  className=\"text-blue-600\"
                                />
                                <span className=\"text-sm text-gray-500\">전체</span>
                              </label>
                            </div>
                          </div>

                          {/* Subcategory Selection */}
                          {filters.category && availableSubcategories.length > 0 && (
                            <div>
                              <div className=\"text-sm font-medium text-gray-700 mb-2\">세부 카테고리</div>
                              <div className=\"space-y-2 max-h-40 overflow-y-auto\">
                                {availableSubcategories.map((subcategory) => (
                                  <label key={subcategory} className=\"flex items-center space-x-2 cursor-pointer\">
                                    <input
                                      type=\"radio\"
                                      name=\"subcategory\"
                                      checked={filters.subcategory === subcategory}
                                      onChange={(e) => {
                                        if (e.target.checked) {
                                          onChange({ subcategory });
                                        }
                                      }}
                                      className=\"text-blue-600\"
                                    />
                                    <span className=\"text-sm text-gray-700\">
                                      {SUBCATEGORY_LABELS[subcategory]}
                                    </span>
                                  </label>
                                ))}
                                <label className=\"flex items-center space-x-2 cursor-pointer\">
                                  <input
                                    type=\"radio\"
                                    name=\"subcategory\"
                                    checked={!filters.subcategory}
                                    onChange={() => onChange({ subcategory: undefined })}
                                    className=\"text-blue-600\"
                                  />
                                  <span className=\"text-sm text-gray-500\">전체</span>
                                </label>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {section.id === 'license' && (
                        <div className=\"space-y-3\">
                          {Object.values(LicenseType).map((license) => (
                            <label key={license} className=\"flex items-center space-x-3 cursor-pointer\">
                              <input
                                type=\"checkbox\"
                                checked={filters.license_type === license}
                                onChange={(e) => {
                                  onChange({ 
                                    license_type: e.target.checked ? license : undefined 
                                  });
                                }}
                                className=\"text-blue-600 rounded\"
                              />
                              <div className=\"flex items-center gap-2\">
                                {license === LicenseType.FREE ? (
                                  <Check className=\"w-4 h-4 text-green-500\" />
                                ) : (
                                  <Lock className=\"w-4 h-4 text-gray-500\" />
                                )}
                                <span className=\"text-sm text-gray-700\">
                                  {LICENSE_LABELS[license]}
                                </span>
                              </div>
                            </label>
                          ))}
                        </div>
                      )}

                      {section.id === 'difficulty' && (
                        <div className=\"space-y-3\">
                          {Object.values(DifficultyLevel).map((difficulty) => (
                            <label key={difficulty} className=\"flex items-center space-x-3 cursor-pointer\">
                              <input
                                type=\"radio\"
                                name=\"difficulty\"
                                checked={filters.difficulty_level === difficulty}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    onChange({ difficulty_level: difficulty });
                                  }
                                }}
                                className=\"text-blue-600\"
                              />
                              <span className=\"text-sm text-gray-700\">
                                {DIFFICULTY_LABELS[difficulty]}
                              </span>
                            </label>
                          ))}
                          <label className=\"flex items-center space-x-3 cursor-pointer\">
                            <input
                              type=\"radio\"
                              name=\"difficulty\"
                              checked={!filters.difficulty_level}
                              onChange={() => onChange({ difficulty_level: undefined })}
                              className=\"text-blue-600\"
                            />
                            <span className=\"text-sm text-gray-500\">전체</span>
                          </label>
                        </div>
                      )}

                      {section.id === 'rating' && (
                        <div className=\"space-y-4\">
                          <div className=\"text-sm text-gray-600\">최소 평점: {filters.min_rating || 0}점</div>
                          <Slider
                            value={[filters.min_rating || 0]}
                            onValueChange={([value]) => onChange({ min_rating: value > 0 ? value : undefined })}
                            min={0}
                            max={5}
                            step={0.5}
                            className=\"w-full\"
                          />
                          <div className=\"flex items-center justify-between text-xs text-gray-500\">
                            <span>0점</span>
                            <span>5점</span>
                          </div>
                        </div>
                      )}

                      {section.id === 'features' && (
                        <div className=\"space-y-3\">
                          <label className=\"flex items-center space-x-3 cursor-pointer\">
                            <input
                              type=\"checkbox\"
                              checked={filters.is_featured || false}
                              onChange={(e) => onChange({ 
                                is_featured: e.target.checked ? true : undefined 
                              })}
                              className=\"text-yellow-600 rounded\"
                            />
                            <div className=\"flex items-center gap-2\">
                              <Crown className=\"w-4 h-4 text-yellow-500\" />
                              <span className=\"text-sm text-gray-700\">추천 템플릿만</span>
                            </div>
                          </label>
                        </div>
                      )}

                      {section.id === 'tags' && (
                        <div className=\"space-y-4\">
                          <TagInput
                            value={filters.tags}
                            onChange={(tags) => onChange({ tags })}
                            placeholder=\"태그 입력 후 Enter...\"
                            suggestions={tagSuggestions}
                          />
                          
                          {tagSuggestions.length > 0 && (
                            <div>
                              <div className=\"text-sm text-gray-600 mb-2\">인기 태그</div>
                              <div className=\"flex flex-wrap gap-1\">
                                {tagSuggestions.slice(0, 10).map((tag) => (
                                  <button
                                    key={tag}
                                    onClick={() => {
                                      if (!filters.tags.includes(tag)) {
                                        onChange({ tags: [...filters.tags, tag] });
                                      }
                                    }}
                                    disabled={filters.tags.includes(tag)}
                                    className={cn(
                                      'px-2 py-1 rounded-md text-xs transition-colors',
                                      filters.tags.includes(tag)
                                        ? 'bg-blue-100 text-blue-800 cursor-not-allowed'
                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer'
                                    )}
                                  >
                                    #{tag}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {section.id === 'date' && (
                        <div className=\"space-y-4\">
                          <DateRangePicker
                            value={filters.date_range}
                            onChange={(range) => onChange({ date_range: range })}
                            placeholder=\"날짜 범위 선택...\"
                          />
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TemplateFilters;