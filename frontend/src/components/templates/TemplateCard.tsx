// Template Card Component
// AIPortal Canvas Template Library - 템플릿 카드 컴포넌트

import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  Heart, Download, Eye, Star, Play, MoreVertical, 
  Crown, TrendingUp, Sparkles, Zap, Users, Clock,
  Palette, Tag, User, Calendar, Award, Lock, Check
} from 'lucide-react';

import {
  TemplateResponse,
  LicenseType,
  DifficultyLevel,
  LICENSE_LABELS,
  DIFFICULTY_LABELS,
  CATEGORY_LABELS
} from '../../types/template';

import { cn } from '../../utils/cn';
import { formatNumber, formatDate } from '../../utils/format';
import Tooltip from '../ui/Tooltip';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import Dropdown from '../ui/Dropdown';

interface TemplateCardProps {
  template: TemplateResponse;
  onClick?: () => void;
  onApply?: () => void;
  onToggleFavorite?: () => void;
  onShare?: () => void;
  onDownload?: () => void;
  showPreview?: boolean;
  showDetails?: boolean;
  featured?: boolean;
  trending?: boolean;
  compact?: boolean;
  selected?: boolean;
  className?: string;
}

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  onClick,
  onApply,
  onToggleFavorite,
  onShare,
  onDownload,
  showPreview = true,
  showDetails = true,
  featured = false,
  trending = false,
  compact = false,
  selected = false,
  className
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [isFavorited, setIsFavorited] = useState(false);

  // Handlers
  const handleCardClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    onClick?.();
  }, [onClick]);

  const handleApplyClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onApply?.();
  }, [onApply]);

  const handleFavoriteClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsFavorited(!isFavorited);
    onToggleFavorite?.();
  }, [isFavorited, onToggleFavorite]);

  const handleShareClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onShare?.();
  }, [onShare]);

  const handleDownloadClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload?.();
  }, [onDownload]);

  // 라이선스 타입에 따른 스타일
  const licenseColor = {
    [LicenseType.FREE]: 'text-green-600 bg-green-50 border-green-200',
    [LicenseType.PREMIUM]: 'text-blue-600 bg-blue-50 border-blue-200',
    [LicenseType.PRO]: 'text-purple-600 bg-purple-50 border-purple-200',
    [LicenseType.ENTERPRISE]: 'text-orange-600 bg-orange-50 border-orange-200',
    [LicenseType.CUSTOM]: 'text-gray-600 bg-gray-50 border-gray-200'
  }[template.license_type] || 'text-gray-600 bg-gray-50 border-gray-200';

  // 난이도에 따른 색상
  const difficultyColor = {
    [DifficultyLevel.BEGINNER]: 'text-green-600',
    [DifficultyLevel.INTERMEDIATE]: 'text-yellow-600', 
    [DifficultyLevel.ADVANCED]: 'text-orange-600',
    [DifficultyLevel.EXPERT]: 'text-red-600'
  }[template.difficulty_level] || 'text-gray-600';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'group relative bg-white rounded-xl border border-gray-200 overflow-hidden cursor-pointer transition-all duration-200',
        'hover:border-gray-300 hover:shadow-lg',
        selected && 'ring-2 ring-blue-500 border-blue-300',
        compact ? 'p-3' : 'p-4',
        className
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleCardClick}
    >
      {/* Special Badges */}
      <div className=\"absolute top-3 left-3 z-10 flex flex-col gap-1\">
        {featured && (
          <Badge
            variant=\"warning\"
            size=\"sm\"
            className=\"flex items-center gap-1 bg-yellow-500 text-white\"
          >
            <Crown className=\"w-3 h-3\" />
            추천
          </Badge>
        )}
        {trending && (
          <Badge
            variant=\"danger\"
            size=\"sm\"
            className=\"flex items-center gap-1 bg-red-500 text-white\"
          >
            <TrendingUp className=\"w-3 h-3\" />
            인기
          </Badge>
        )}
        {template.license_type !== LicenseType.FREE && (
          <Badge
            variant=\"primary\"
            size=\"sm\"
            className=\"flex items-center gap-1\"
          >
            <Lock className=\"w-3 h-3\" />
            {LICENSE_LABELS[template.license_type]}
          </Badge>
        )}
      </div>

      {/* Actions */}
      <div className=\"absolute top-3 right-3 z-10 flex items-center gap-1\">
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ 
            opacity: isHovered ? 1 : 0,
            scale: isHovered ? 1 : 0.8
          }}
          transition={{ duration: 0.15 }}
          onClick={handleFavoriteClick}
          className={cn(
            'p-1.5 rounded-full backdrop-blur-sm transition-colors',
            isFavorited 
              ? 'bg-red-500 text-white shadow-md' 
              : 'bg-white/80 text-gray-600 hover:bg-white hover:text-red-500 shadow-sm'
          )}
        >
          <Heart className={cn('w-4 h-4', isFavorited && 'fill-current')} />
        </motion.button>

        <Dropdown
          trigger={
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ 
                opacity: isHovered ? 1 : 0,
                scale: isHovered ? 1 : 0.8
              }}
              transition={{ duration: 0.15, delay: 0.05 }}
              className=\"p-1.5 rounded-full bg-white/80 text-gray-600 hover:bg-white backdrop-blur-sm shadow-sm transition-colors\"
            >
              <MoreVertical className=\"w-4 h-4\" />
            </motion.button>
          }
          align=\"right\"
        >
          <div className=\"w-48\">
            <button
              onClick={handleShareClick}
              className=\"flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100\"
            >
              <Eye className=\"w-4 h-4\" />
              미리보기
            </button>
            <button
              onClick={handleDownloadClick}
              className=\"flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100\"
            >
              <Download className=\"w-4 h-4\" />
              다운로드
            </button>
            <button
              onClick={handleShareClick}
              className=\"flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100\"
            >
              <Users className=\"w-4 h-4\" />
              공유하기
            </button>
          </div>
        </Dropdown>
      </div>

      {/* Template Preview */}
      {showPreview && (
        <div className={cn(
          'relative rounded-lg overflow-hidden mb-3',
          compact ? 'aspect-[4/3]' : 'aspect-[4/3]'
        )}>
          {!imageError && template.thumbnail_url ? (
            <>
              {!imageLoaded && (
                <div className=\"absolute inset-0 bg-gray-100 animate-pulse flex items-center justify-center\">
                  <Palette className=\"w-8 h-8 text-gray-400\" />
                </div>
              )}
              <img
                src={template.thumbnail_url}
                alt={template.name}
                className={cn(
                  'w-full h-full object-cover transition-all duration-300',
                  imageLoaded ? 'opacity-100' : 'opacity-0',
                  isHovered && 'scale-105'
                )}
                onLoad={() => setImageLoaded(true)}
                onError={() => setImageError(true)}
              />
            </>
          ) : (
            <div className=\"w-full h-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center\">
              <div className=\"text-center\">
                <Palette className=\"w-8 h-8 text-gray-400 mx-auto mb-2\" />
                <div className=\"text-xs text-gray-500\">미리보기 없음</div>
              </div>
            </div>
          )}

          {/* Play Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: isHovered ? 1 : 0 }}
            transition={{ duration: 0.2 }}
            className=\"absolute inset-0 bg-black/20 flex items-center justify-center\"
          >
            <div className=\"bg-white/90 rounded-full p-3 backdrop-blur-sm\">
              <Play className=\"w-6 h-6 text-gray-800 ml-0.5\" />
            </div>
          </motion.div>
        </div>
      )}

      {/* Template Info */}
      <div className=\"space-y-2\">
        {/* Title */}
        <h3 className={cn(
          'font-semibold text-gray-900 line-clamp-2',
          compact ? 'text-sm' : 'text-base'
        )}>
          {template.name}
        </h3>

        {/* Description */}
        {showDetails && template.description && !compact && (
          <p className=\"text-sm text-gray-600 line-clamp-2\">
            {template.description}
          </p>
        )}

        {/* Tags */}
        {showDetails && template.tags && template.tags.length > 0 && !compact && (
          <div className=\"flex items-center gap-1 overflow-hidden\">
            <Tag className=\"w-3 h-3 text-gray-400 flex-shrink-0\" />
            <div className=\"flex gap-1 overflow-hidden\">
              {template.tags.slice(0, 3).map((tag, index) => (
                <span
                  key={index}
                  className=\"inline-block px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-md truncate\"
                >
                  {tag}
                </span>
              ))}
              {template.tags.length > 3 && (
                <span className=\"text-xs text-gray-500\">
                  +{template.tags.length - 3}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Stats */}
        {showDetails && (
          <div className=\"flex items-center gap-4 text-xs text-gray-500\">
            {/* Rating */}
            {template.stats.average_rating > 0 && (
              <Tooltip content={`${template.stats.rating_count}개 리뷰`}>
                <div className=\"flex items-center gap-1\">
                  <Star className=\"w-3 h-3 text-yellow-400 fill-current\" />
                  <span>{template.stats.average_rating.toFixed(1)}</span>
                </div>
              </Tooltip>
            )}

            {/* Usage Count */}
            <Tooltip content=\"사용 횟수\">
              <div className=\"flex items-center gap-1\">
                <Zap className=\"w-3 h-3\" />
                <span>{formatNumber(template.stats.usage_count)}</span>
              </div>
            </Tooltip>

            {/* View Count */}
            <Tooltip content=\"조회수\">
              <div className=\"flex items-center gap-1\">
                <Eye className=\"w-3 h-3\" />
                <span>{formatNumber(template.stats.view_count)}</span>
              </div>
            </Tooltip>

            {/* Difficulty */}
            <Tooltip content=\"난이도\">
              <div className={cn('flex items-center gap-1', difficultyColor)}>
                <Award className=\"w-3 h-3\" />
                <span>{DIFFICULTY_LABELS[template.difficulty_level]}</span>
              </div>
            </Tooltip>
          </div>
        )}

        {/* Creator & Date */}
        {showDetails && !compact && (
          <div className=\"flex items-center justify-between text-xs text-gray-500\">
            <div className=\"flex items-center gap-1\">
              <User className=\"w-3 h-3\" />
              <span className=\"truncate\">{template.creator.username}</span>
              {template.creator.is_verified && (
                <Check className=\"w-3 h-3 text-blue-500\" />
              )}
            </div>
            <div className=\"flex items-center gap-1\">
              <Calendar className=\"w-3 h-3\" />
              <span>{formatDate(template.created_at)}</span>
            </div>
          </div>
        )}

        {/* License Info */}
        {showDetails && !compact && (
          <div className={cn(
            'inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs border',
            licenseColor
          )}>
            {template.license_type === LicenseType.FREE ? (
              <Check className=\"w-3 h-3\" />
            ) : (
              <Lock className=\"w-3 h-3\" />
            )}
            {LICENSE_LABELS[template.license_type]}
          </div>
        )}
      </div>

      {/* Apply Button */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ 
          opacity: isHovered || compact ? 1 : 0,
          y: isHovered || compact ? 0 : 10
        }}
        transition={{ duration: 0.2, delay: 0.1 }}
        className=\"mt-3 pt-3 border-t border-gray-100\"
      >
        <Button
          variant=\"primary\"
          size=\"sm\"
          className=\"w-full\"
          onClick={handleApplyClick}
        >
          <Play className=\"w-4 h-4 mr-2\" />
          템플릿 적용
        </Button>
      </motion.div>

      {/* Hover Glow Effect */}
      <div className={cn(
        'absolute inset-0 rounded-xl transition-opacity duration-300 pointer-events-none',
        'bg-gradient-to-r from-blue-500/5 to-purple-500/5',
        isHovered ? 'opacity-100' : 'opacity-0'
      )} />
    </motion.div>
  );
};

export default TemplateCard;