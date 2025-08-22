/**
 * 공통 스타일링 유틸리티 - 중복된 Tailwind 클래스 조합을 재사용 가능한 함수로 정리
 */

/**
 * 버튼 스타일 변형
 */
export const buttonVariants = {
  primary: 'bg-primary-600 hover:bg-primary-700 text-white font-medium px-4 py-2 rounded-lg transition-colors duration-200',
  secondary: 'bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-100 font-medium px-4 py-2 rounded-lg transition-colors duration-200',
  outline: 'border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium px-4 py-2 rounded-lg transition-colors duration-200',
  ghost: 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium px-4 py-2 rounded-lg transition-colors duration-200',
  danger: 'bg-red-600 hover:bg-red-700 text-white font-medium px-4 py-2 rounded-lg transition-colors duration-200',
  success: 'bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-2 rounded-lg transition-colors duration-200'
};

/**
 * 버튼 크기 변형
 */
export const buttonSizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
  xl: 'px-8 py-4 text-lg'
};

/**
 * 아이콘 버튼 스타일
 */
export const iconButtonVariants = {
  primary: 'p-2 text-primary-600 hover:text-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-all duration-200',
  secondary: 'p-2 text-slate-600 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-300 dark:hover:bg-slate-800 rounded-lg transition-all duration-200',
  ghost: 'p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 dark:hover:text-slate-300 rounded-lg transition-all duration-200',
  danger: 'p-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200'
};

/**
 * 카드 스타일
 */
export const cardVariants = {
  default: 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm',
  elevated: 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg',
  outlined: 'bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-lg',
  ghost: 'bg-slate-50 dark:bg-slate-900/50 rounded-lg'
};

/**
 * 입력 필드 스타일
 */
export const inputVariants = {
  default: 'w-full px-3 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors duration-200',
  error: 'w-full px-3 py-2 border border-red-300 dark:border-red-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors duration-200',
  success: 'w-full px-3 py-2 border border-green-300 dark:border-green-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors duration-200'
};

/**
 * 뱃지 스타일
 */
export const badgeVariants = {
  primary: 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300',
  secondary: 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  success: 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300',
  warning: 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300',
  danger: 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-300',
  info: 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300'
};

/**
 * 텍스트 스타일
 */
export const textVariants = {
  h1: 'text-3xl font-bold text-slate-900 dark:text-slate-100',
  h2: 'text-2xl font-semibold text-slate-900 dark:text-slate-100',
  h3: 'text-xl font-semibold text-slate-900 dark:text-slate-100',
  h4: 'text-lg font-medium text-slate-900 dark:text-slate-100',
  body: 'text-sm text-slate-700 dark:text-slate-300',
  caption: 'text-xs text-slate-500 dark:text-slate-400',
  muted: 'text-xs text-slate-400 dark:text-slate-500'
};

/**
 * 레이아웃 스타일
 */
export const layoutStyles = {
  container: 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8',
  containerSm: 'max-w-3xl mx-auto px-4 sm:px-6',
  flexCenter: 'flex items-center justify-center',
  flexBetween: 'flex items-center justify-between',
  flexCol: 'flex flex-col',
  gridCols: {
    1: 'grid grid-cols-1',
    2: 'grid grid-cols-1 md:grid-cols-2',
    3: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
  }
};

/**
 * 애니메이션 스타일
 */
export const animationStyles = {
  fadeIn: 'animate-in fade-in duration-200',
  slideIn: 'animate-in slide-in-from-bottom-4 duration-300',
  slideUp: 'animate-in slide-in-from-top-4 duration-300',
  scaleIn: 'animate-in zoom-in-95 duration-200',
  fadeOut: 'animate-out fade-out duration-200',
  slideOut: 'animate-out slide-out-to-bottom-4 duration-300',
  scaleOut: 'animate-out zoom-out-95 duration-200'
};

/**
 * 반응형 텍스트 크기
 */
export const responsiveText = {
  xs: 'text-xs sm:text-sm',
  sm: 'text-sm sm:text-base',
  base: 'text-base sm:text-lg',
  lg: 'text-lg sm:text-xl',
  xl: 'text-xl sm:text-2xl',
  '2xl': 'text-2xl sm:text-3xl'
};

/**
 * 모바일 최적화 스타일
 */
export const mobileStyles = {
  padding: 'px-2 sm:px-4',
  margin: 'mx-2 sm:mx-4',
  text: 'text-sm sm:text-base',
  button: 'px-3 py-2 sm:px-4 sm:py-2',
  spacing: 'space-y-2 sm:space-y-4'
};

/**
 * 조건부 클래스 결합 유틸리티
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

/**
 * 버튼 클래스 생성기
 */
export function getButtonClass(
  variant: keyof typeof buttonVariants = 'primary',
  size: keyof typeof buttonSizes = 'md',
  disabled: boolean = false,
  className?: string
): string {
  const baseClasses = buttonVariants[variant];
  const sizeClasses = buttonSizes[size];
  const disabledClasses = disabled ? 'opacity-50 cursor-not-allowed' : '';
  
  return cn(baseClasses, sizeClasses, disabledClasses, className);
}

/**
 * 아이콘 버튼 클래스 생성기
 */
export function getIconButtonClass(
  variant: keyof typeof iconButtonVariants = 'secondary',
  disabled: boolean = false,
  className?: string
): string {
  const baseClasses = iconButtonVariants[variant];
  const disabledClasses = disabled ? 'opacity-50 cursor-not-allowed' : '';
  
  return cn(baseClasses, disabledClasses, className);
}

/**
 * 카드 클래스 생성기
 */
export function getCardClass(
  variant: keyof typeof cardVariants = 'default',
  className?: string
): string {
  return cn(cardVariants[variant], className);
}

/**
 * 뱃지 클래스 생성기
 */
export function getBadgeClass(
  variant: keyof typeof badgeVariants = 'secondary',
  className?: string
): string {
  return cn(badgeVariants[variant], className);
}