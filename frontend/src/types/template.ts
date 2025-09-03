// Template System Type Definitions
// AIPortal Canvas Template Library - TypeScript 타입 정의

// ===== Enums =====

export enum TemplateCategory {
  BUSINESS = 'business',
  SOCIAL_MEDIA = 'social_media',
  EDUCATION = 'education',
  EVENT = 'event',
  PERSONAL = 'personal',
  CREATIVE = 'creative',
  MARKETING = 'marketing',
  PRESENTATION = 'presentation'
}

export enum TemplateSubcategory {
  // Business
  BUSINESS_CARD = 'business_card',
  BROCHURE = 'brochure',
  FLYER = 'flyer',
  PRESENTATION = 'presentation',
  INVOICE = 'invoice',
  LETTERHEAD = 'letterhead',
  
  // Social Media
  INSTAGRAM_POST = 'instagram_post',
  INSTAGRAM_STORY = 'instagram_story',
  FACEBOOK_POST = 'facebook_post',
  FACEBOOK_COVER = 'facebook_cover',
  TWITTER_POST = 'twitter_post',
  YOUTUBE_THUMBNAIL = 'youtube_thumbnail',
  LINKEDIN_POST = 'linkedin_post',
  
  // Education
  INFOGRAPHIC = 'infographic',
  DIAGRAM = 'diagram',
  CHART = 'chart',
  WORKSHEET = 'worksheet',
  CERTIFICATE = 'certificate',
  PRESENTATION_SLIDE = 'presentation_slide',
  
  // Event
  POSTER = 'poster',
  TICKET = 'ticket',
  INVITATION = 'invitation',
  BANNER = 'banner',
  PROGRAM = 'program',
  BADGE = 'badge',
  
  // Personal
  BIRTHDAY = 'birthday',
  WEDDING = 'wedding',
  TRAVEL = 'travel',
  HOBBY = 'hobby',
  FAMILY = 'family',
  ANNIVERSARY = 'anniversary'
}

export enum TemplateStatus {
  DRAFT = 'draft',
  PENDING_REVIEW = 'pending_review',
  APPROVED = 'approved',
  FEATURED = 'featured',
  ARCHIVED = 'archived',
  REJECTED = 'rejected'
}

export enum LicenseType {
  FREE = 'free',
  PREMIUM = 'premium',
  PRO = 'pro',
  ENTERPRISE = 'enterprise',
  CUSTOM = 'custom'
}

export enum DifficultyLevel {
  BEGINNER = 'beginner',
  INTERMEDIATE = 'intermediate',
  ADVANCED = 'advanced',
  EXPERT = 'expert'
}

export enum SortBy {
  CREATED_DESC = 'created_desc',
  CREATED_ASC = 'created_asc',
  UPDATED_DESC = 'updated_desc',
  RATING_DESC = 'rating_desc',
  USAGE_DESC = 'usage_desc',
  NAME_ASC = 'name_asc',
  NAME_DESC = 'name_desc'
}

// ===== 기본 타입 =====

export interface TemplateDimensions {
  width: number;
  height: number;
}

export interface ColorPalette {
  name: string;
  colors: string[];
  description?: string;
}

export interface CustomizableElement {
  element_id: string;
  element_type: string;
  customization_types: string[];
  default_value?: any;
  constraints?: Record<string, any>;
}

export interface LicenseDetails {
  license_text: string;
  commercial_usage: boolean;
  attribution_required: boolean;
  redistribution_allowed: boolean;
  usage_limit?: number;
  expires_at?: string;
}

// ===== 요청 타입 =====

export interface TemplateSearchRequest {
  query?: string;
  category?: TemplateCategory;
  subcategory?: TemplateSubcategory;
  tags?: string[];
  license_type?: LicenseType;
  difficulty_level?: DifficultyLevel;
  is_featured?: boolean;
  min_rating?: number;
  created_after?: string;
  created_before?: string;
  sort_by?: SortBy;
  page?: number;
  page_size?: number;
}

export interface TemplateCreateRequest {
  name: string;
  description?: string;
  keywords?: string[];
  category: TemplateCategory;
  subcategory: TemplateSubcategory;
  tags?: string[];
  canvas_data: Record<string, any>;
  thumbnail_url?: string;
  preview_images?: string[];
  customizable_elements?: CustomizableElement[];
  color_palettes?: ColorPalette[];
  font_suggestions?: string[];
  dimensions: TemplateDimensions;
  aspect_ratio?: string;
  orientation?: string;
  difficulty_level?: DifficultyLevel;
  license_type?: LicenseType;
  license_details?: LicenseDetails;
  is_public?: boolean;
}

export interface TemplateUpdateRequest extends Partial<TemplateCreateRequest> {}

export interface TemplateApplyRequest {
  canvas_id: string;
  customizations?: Record<string, any>;
  preset_id?: string;
}

export interface TemplateCustomizationRequest {
  customizations: Record<string, any>;
}

// ===== 응답 타입 =====

export interface TemplateStats {
  view_count: number;
  download_count: number;
  usage_count: number;
  average_rating: number;
  rating_count: number;
}

export interface TemplateCreator {
  id: string;
  username: string;
  display_name?: string;
  avatar_url?: string;
  is_verified: boolean;
}

export interface TemplateResponse {
  id: string;
  name: string;
  description?: string;
  keywords?: string[];
  category: TemplateCategory;
  subcategory: TemplateSubcategory;
  tags?: string[];
  status: TemplateStatus;
  is_public: boolean;
  is_featured: boolean;
  thumbnail_url?: string;
  preview_images?: string[];
  dimensions: TemplateDimensions;
  aspect_ratio?: string;
  orientation?: string;
  difficulty_level: DifficultyLevel;
  license_type: LicenseType;
  stats: TemplateStats;
  creator: TemplateCreator;
  created_at: string;
  updated_at: string;
  published_at?: string;
}

export interface TemplateDetailResponse extends TemplateResponse {
  canvas_data: Record<string, any>;
  customizable_elements?: CustomizableElement[];
  color_palettes?: ColorPalette[];
  font_suggestions?: string[];
  license_details?: LicenseDetails;
  version: string;
  parent_template_id?: string;
}

export interface TemplateSearchResponse {
  templates: TemplateResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ===== 리뷰 시스템 타입 =====

export interface TemplateReviewRequest {
  rating: number;
  title?: string;
  comment?: string;
  is_recommended?: boolean;
  review_categories?: string[];
}

export interface TemplateReviewResponse {
  id: string;
  rating: number;
  title?: string;
  comment?: string;
  is_recommended: boolean;
  helpful_count: number;
  not_helpful_count: number;
  review_categories?: string[];
  user_id: string;
  username: string;
  created_at: string;
  updated_at: string;
}

// ===== 컬렉션 시스템 타입 =====

export interface CollectionCreateRequest {
  name: string;
  description?: string;
  cover_image_url?: string;
  is_public?: boolean;
}

export interface CollectionUpdateRequest extends Partial<CollectionCreateRequest> {}

export interface CollectionItemRequest {
  template_id: string;
  personal_notes?: string;
}

export interface CollectionResponse {
  id: string;
  name: string;
  description?: string;
  cover_image_url?: string;
  is_public: boolean;
  is_featured: boolean;
  template_count: number;
  view_count: number;
  follower_count: number;
  user_id: string;
  username: string;
  created_at: string;
  updated_at: string;
}

// ===== 커스터마이징 프리셋 타입 =====

export interface CustomizationPresetRequest {
  name: string;
  description?: string;
  customization_config: Record<string, any>;
}

export interface CustomizationPresetResponse {
  id: string;
  name: string;
  description?: string;
  customization_config: Record<string, any>;
  preview_url?: string;
  usage_count: number;
  is_official: boolean;
  created_at: string;
}

// ===== 분석 타입 =====

export interface TemplateAnalyticsResponse {
  template_id: string;
  period_type: string;
  period_start: string;
  period_end: string;
  views: number;
  downloads: number;
  applications: number;
  conversions: number;
  new_users: number;
  returning_users: number;
  premium_users: number;
  country_breakdown: Record<string, number>;
  avg_load_time?: number;
  avg_apply_time?: number;
  bounce_rate?: number;
}

// ===== 카테고리 관리 타입 =====

export interface CategoryInfo {
  value: string;
  label: string;
  subcategories?: SubcategoryInfo[];
}

export interface SubcategoryInfo {
  value: string;
  label: string;
}

export interface CategoryResponse {
  id: string;
  name: string;
  slug: string;
  description?: string;
  parent_id?: string;
  level: number;
  sort_order: number;
  icon_url?: string;
  color_hex?: string;
  template_count: number;
  is_active: boolean;
}

export interface TagResponse {
  id: string;
  name: string;
  slug: string;
  description?: string;
  tag_type?: string;
  color_hex?: string;
  usage_count: number;
  is_trending: boolean;
}

// ===== 필터 및 UI 상태 타입 =====

export interface TemplateFilters {
  category?: TemplateCategory;
  subcategory?: TemplateSubcategory;
  tags: string[];
  license_type?: LicenseType;
  difficulty_level?: DifficultyLevel;
  is_featured?: boolean;
  min_rating?: number;
  price_range?: [number, number];
  date_range?: [string, string];
}

export interface TemplateSortOptions {
  sort_by: SortBy;
  order: 'asc' | 'desc';
}

export interface TemplateViewMode {
  view: 'grid' | 'list' | 'masonry';
  columns: 2 | 3 | 4 | 5;
  show_preview: boolean;
  show_details: boolean;
}

// ===== 템플릿 상호작용 타입 =====

export interface TemplateInteraction {
  template_id: string;
  action: 'view' | 'like' | 'download' | 'apply' | 'share';
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface TemplateFavorite {
  template_id: string;
  is_favorite: boolean;
  notes?: string;
  tags?: string[];
  created_at: string;
}

// ===== 템플릿 커스터마이징 타입 =====

export interface TemplateCustomization {
  element_id: string;
  property: string;
  old_value: any;
  new_value: any;
  timestamp: string;
}

export interface TemplateCustomizationSession {
  template_id: string;
  session_id: string;
  customizations: TemplateCustomization[];
  started_at: string;
  last_updated: string;
  is_saved: boolean;
}

// ===== 에러 타입 =====

export interface TemplateError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// ===== 유틸리티 타입 =====

export type TemplateId = string;
export type CategoryId = string;
export type TagName = string;
export type UserId = string;

// 카테고리 레이블 매핑
export const CATEGORY_LABELS: Record<TemplateCategory, string> = {
  [TemplateCategory.BUSINESS]: '비즈니스',
  [TemplateCategory.SOCIAL_MEDIA]: '소셜 미디어',
  [TemplateCategory.EDUCATION]: '교육',
  [TemplateCategory.EVENT]: '이벤트',
  [TemplateCategory.PERSONAL]: '개인',
  [TemplateCategory.CREATIVE]: '창작',
  [TemplateCategory.MARKETING]: '마케팅',
  [TemplateCategory.PRESENTATION]: '프레젠테이션'
};

// 서브카테고리 레이블 매핑
export const SUBCATEGORY_LABELS: Record<TemplateSubcategory, string> = {
  // Business
  [TemplateSubcategory.BUSINESS_CARD]: '명함',
  [TemplateSubcategory.BROCHURE]: '브로셔',
  [TemplateSubcategory.FLYER]: '전단지',
  [TemplateSubcategory.PRESENTATION]: '프레젠테이션',
  [TemplateSubcategory.INVOICE]: '청구서',
  [TemplateSubcategory.LETTERHEAD]: '레터헤드',
  
  // Social Media
  [TemplateSubcategory.INSTAGRAM_POST]: '인스타그램 포스트',
  [TemplateSubcategory.INSTAGRAM_STORY]: '인스타그램 스토리',
  [TemplateSubcategory.FACEBOOK_POST]: '페이스북 포스트',
  [TemplateSubcategory.FACEBOOK_COVER]: '페이스북 커버',
  [TemplateSubcategory.TWITTER_POST]: '트위터 포스트',
  [TemplateSubcategory.YOUTUBE_THUMBNAIL]: '유튜브 썸네일',
  [TemplateSubcategory.LINKEDIN_POST]: '링크드인 포스트',
  
  // Education
  [TemplateSubcategory.INFOGRAPHIC]: '인포그래픽',
  [TemplateSubcategory.DIAGRAM]: '다이어그램',
  [TemplateSubcategory.CHART]: '차트',
  [TemplateSubcategory.WORKSHEET]: '워크시트',
  [TemplateSubcategory.CERTIFICATE]: '인증서',
  [TemplateSubcategory.PRESENTATION_SLIDE]: '프레젠테이션 슬라이드',
  
  // Event
  [TemplateSubcategory.POSTER]: '포스터',
  [TemplateSubcategory.TICKET]: '티켓',
  [TemplateSubcategory.INVITATION]: '초대장',
  [TemplateSubcategory.BANNER]: '배너',
  [TemplateSubcategory.PROGRAM]: '프로그램',
  [TemplateSubcategory.BADGE]: '배지',
  
  // Personal
  [TemplateSubcategory.BIRTHDAY]: '생일',
  [TemplateSubcategory.WEDDING]: '결혼',
  [TemplateSubcategory.TRAVEL]: '여행',
  [TemplateSubcategory.HOBBY]: '취미',
  [TemplateSubcategory.FAMILY]: '가족',
  [TemplateSubcategory.ANNIVERSARY]: '기념일'
};

// 라이선스 타입 레이블
export const LICENSE_LABELS: Record<LicenseType, string> = {
  [LicenseType.FREE]: '무료',
  [LicenseType.PREMIUM]: '프리미엄',
  [LicenseType.PRO]: '프로',
  [LicenseType.ENTERPRISE]: '기업용',
  [LicenseType.CUSTOM]: '맞춤형'
};

// 난이도 레벨 레이블
export const DIFFICULTY_LABELS: Record<DifficultyLevel, string> = {
  [DifficultyLevel.BEGINNER]: '초급',
  [DifficultyLevel.INTERMEDIATE]: '중급',
  [DifficultyLevel.ADVANCED]: '고급',
  [DifficultyLevel.EXPERT]: '전문가'
};

export default {
  TemplateCategory,
  TemplateSubcategory,
  TemplateStatus,
  LicenseType,
  DifficultyLevel,
  SortBy,
  CATEGORY_LABELS,
  SUBCATEGORY_LABELS,
  LICENSE_LABELS,
  DIFFICULTY_LABELS
};