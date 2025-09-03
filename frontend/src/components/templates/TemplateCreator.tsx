// Template Creator Component
// AIPortal Canvas Template Library - 사용자 템플릿 생성 컴포넌트

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Save, Eye, Share2, Upload, Download, Settings,
  Image as ImageIcon, Type, Palette, Grid, Layers,
  Check, X, AlertTriangle, Info, Sparkles, Crown,
  Lock, Unlock, Tag, Calendar, User, Star, Zap
} from 'lucide-react';

import {
  TemplateCreateRequest,
  TemplateCategory,
  TemplateSubcategory,
  LicenseType,
  DifficultyLevel,
  ColorPalette,
  CustomizableElement,
  TemplateDimensions,
  CATEGORY_LABELS,
  SUBCATEGORY_LABELS,
  LICENSE_LABELS,
  DIFFICULTY_LABELS
} from '../../types/template';

import { cn } from '../../utils/cn';
import { useTemplateStore } from '../../stores/templateStore';
import { useCanvasStore } from '../../stores/canvasStore';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Textarea from '../ui/Textarea';
import Select from '../ui/Select';
import Checkbox from '../ui/Checkbox';
import TagInput from '../ui/TagInput';
import ColorPicker from '../ui/ColorPicker';
import FileUpload from '../ui/FileUpload';
import Badge from '../ui/Badge';
import Tabs from '../ui/Tabs';
import Card from '../ui/Card';
import Modal from '../ui/Modal';
import LoadingSpinner from '../ui/LoadingSpinner';
import Tooltip from '../ui/Tooltip';

interface TemplateCreatorProps {
  canvasId?: string;
  initialCanvasData?: Record<string, any>;
  onSave?: (template: any) => void;
  onCancel?: () => void;
  className?: string;
}

interface ValidationError {
  field: string;
  message: string;
}

interface CreationStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  completed: boolean;
  optional?: boolean;
}

const TemplateCreator: React.FC<TemplateCreatorProps> = ({
  canvasId,
  initialCanvasData,
  onSave,
  onCancel,
  className
}) => {
  // State
  const [currentStep, setCurrentStep] = useState(0);
  const [templateData, setTemplateData] = useState<Partial<TemplateCreateRequest>>({
    name: '',
    description: '',
    category: TemplateCategory.CREATIVE,
    subcategory: undefined,
    tags: [],
    keywords: [],
    difficulty_level: DifficultyLevel.BEGINNER,
    license_type: LicenseType.FREE,
    is_public: true,
    canvas_data: initialCanvasData || {},
    dimensions: { width: 1920, height: 1080 },
    customizable_elements: [],
    color_palettes: [],
    font_suggestions: []
  });
  
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null);
  const [previewImages, setPreviewImages] = useState<File[]>([]);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [autoAnalysis, setAutoAnalysis] = useState(true);
  const [analysisResults, setAnalysisResults] = useState<any>(null);

  // Hooks
  const { createTemplate, extractTemplateMetadata } = useTemplateStore();
  const { currentCanvas } = useCanvasStore();

  // Creation steps
  const steps: CreationStep[] = [
    {
      id: 'basic',
      title: '기본 정보',
      description: '템플릿의 기본 정보를 입력하세요',
      icon: <Info className=\"w-5 h-5\" />,
      completed: !!(templateData.name && templateData.category)
    },
    {
      id: 'categorization',
      title: '분류 및 태그',
      description: '템플릿을 쉽게 찾을 수 있도록 분류하세요',
      icon: <Tag className=\"w-5 h-5\" />,
      completed: !!(templateData.category && templateData.tags && templateData.tags.length > 0)
    },
    {
      id: 'design',
      title: '디자인 설정',
      description: '색상, 폰트, 커스터마이징 옵션을 설정하세요',
      icon: <Palette className=\"w-5 h-5\" />,
      completed: !!(templateData.color_palettes && templateData.color_palettes.length > 0),
      optional: true
    },
    {
      id: 'media',
      title: '미디어 및 미리보기',
      description: '썸네일과 미리보기 이미지를 업로드하세요',
      icon: <ImageIcon className=\"w-5 h-5\" />,
      completed: !!thumbnailFile,
      optional: true
    },
    {
      id: 'settings',
      title: '공개 설정',
      description: '라이선스와 공개 범위를 설정하세요',
      icon: <Settings className=\"w-5 h-5\" />,
      completed: !!(templateData.license_type && templateData.is_public !== undefined)
    }
  ];

  // Initialize canvas data
  useEffect(() => {
    if (currentCanvas && !initialCanvasData) {
      setTemplateData(prev => ({
        ...prev,
        canvas_data: currentCanvas.canvas_data,
        dimensions: {
          width: currentCanvas.stage_config.width,
          height: currentCanvas.stage_config.height
        }
      }));
    }
  }, [currentCanvas, initialCanvasData]);

  // Auto-analyze canvas data
  useEffect(() => {
    if (autoAnalysis && templateData.canvas_data) {
      analyzeCanvasData();
    }
  }, [templateData.canvas_data, autoAnalysis]);

  // Canvas data analysis
  const analyzeCanvasData = useCallback(async () => {
    if (!templateData.canvas_data) return;

    try {
      const metadata = await extractTemplateMetadata(
        templateData.name || 'Untitled Template',
        templateData.description,
        templateData.canvas_data
      );

      setAnalysisResults(metadata);

      // Auto-populate based on analysis
      setTemplateData(prev => ({
        ...prev,
        keywords: metadata.keywords || prev.keywords,
        difficulty_level: metadata.complexity_score > 70 
          ? DifficultyLevel.ADVANCED 
          : metadata.complexity_score > 40 
            ? DifficultyLevel.INTERMEDIATE 
            : DifficultyLevel.BEGINNER,
        // Auto-generate color palettes from dominant colors
        color_palettes: metadata.dominant_colors && metadata.dominant_colors.length > 0 ? [
          {
            name: '자동 추출 색상',
            colors: metadata.dominant_colors.slice(0, 5),
            description: '템플릿에서 자동으로 추출된 주요 색상'
          },
          ...prev.color_palettes || []
        ] : prev.color_palettes,
        // Auto-suggest font families
        font_suggestions: metadata.font_families || prev.font_suggestions
      }));

    } catch (error) {
      console.error('Failed to analyze canvas data:', error);
    }
  }, [templateData.canvas_data, templateData.name, templateData.description, extractTemplateMetadata]);

  // Validation
  const validateStep = useCallback((stepIndex: number): ValidationError[] => {
    const errors: ValidationError[] = [];
    const step = steps[stepIndex];

    switch (step.id) {
      case 'basic':
        if (!templateData.name?.trim()) {
          errors.push({ field: 'name', message: '템플릿 이름을 입력해주세요' });
        } else if (templateData.name.length < 2) {
          errors.push({ field: 'name', message: '템플릿 이름은 2자 이상이어야 합니다' });
        } else if (templateData.name.length > 100) {
          errors.push({ field: 'name', message: '템플릿 이름은 100자 이하여야 합니다' });
        }

        if (!templateData.category) {
          errors.push({ field: 'category', message: '카테고리를 선택해주세요' });
        }

        if (templateData.description && templateData.description.length > 1000) {
          errors.push({ field: 'description', message: '설명은 1000자 이하여야 합니다' });
        }
        break;

      case 'categorization':
        if (!templateData.tags || templateData.tags.length === 0) {
          errors.push({ field: 'tags', message: '최소 1개의 태그를 입력해주세요' });
        } else if (templateData.tags.length > 10) {
          errors.push({ field: 'tags', message: '태그는 최대 10개까지 입력할 수 있습니다' });
        }
        break;

      case 'settings':
        if (!templateData.canvas_data || Object.keys(templateData.canvas_data).length === 0) {
          errors.push({ field: 'canvas_data', message: 'Canvas 데이터가 필요합니다' });
        }
        break;
    }

    return errors;
  }, [templateData, steps]);

  // Handlers
  const handleStepChange = useCallback((stepIndex: number) => {
    const errors = validateStep(currentStep);
    
    if (errors.length > 0 && stepIndex > currentStep) {
      setValidationErrors(errors);
      return;
    }

    setValidationErrors([]);
    setCurrentStep(stepIndex);
  }, [currentStep, validateStep]);

  const handleFieldChange = useCallback((field: keyof TemplateCreateRequest, value: any) => {
    setTemplateData(prev => ({ ...prev, [field]: value }));
    
    // Clear validation errors for this field
    setValidationErrors(prev => prev.filter(error => error.field !== field));
  }, []);

  const handleAddColorPalette = useCallback(() => {
    const newPalette: ColorPalette = {
      name: `색상 팔레트 ${(templateData.color_palettes?.length || 0) + 1}`,
      colors: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1'],
      description: '새로운 색상 팔레트'
    };

    handleFieldChange('color_palettes', [...(templateData.color_palettes || []), newPalette]);
  }, [templateData.color_palettes, handleFieldChange]);

  const handleRemoveColorPalette = useCallback((index: number) => {
    handleFieldChange('color_palettes', templateData.color_palettes?.filter((_, i) => i !== index) || []);
  }, [templateData.color_palettes, handleFieldChange]);

  const handleUpdateColorPalette = useCallback((index: number, updatedPalette: ColorPalette) => {
    const updatedPalettes = [...(templateData.color_palettes || [])];
    updatedPalettes[index] = updatedPalette;
    handleFieldChange('color_palettes', updatedPalettes);
  }, [templateData.color_palettes, handleFieldChange]);

  const handleThumbnailUpload = useCallback((file: File) => {
    setThumbnailFile(file);
    
    // Generate preview URL
    const previewUrl = URL.createObjectURL(file);
    handleFieldChange('thumbnail_url', previewUrl);
  }, [handleFieldChange]);

  const handlePreviewImagesUpload = useCallback((files: File[]) => {
    setPreviewImages(files);
    
    // Generate preview URLs
    const previewUrls = files.map(file => URL.createObjectURL(file));
    handleFieldChange('preview_images', previewUrls);
  }, [handleFieldChange]);

  const handleSubmit = useCallback(async () => {
    // Validate all steps
    const allErrors: ValidationError[] = [];
    steps.forEach((step, index) => {
      if (!step.optional) {
        allErrors.push(...validateStep(index));
      }
    });

    if (allErrors.length > 0) {
      setValidationErrors(allErrors);
      return;
    }

    setIsSubmitting(true);

    try {
      // Create template request
      const request: TemplateCreateRequest = {
        name: templateData.name!,
        description: templateData.description,
        keywords: templateData.keywords,
        category: templateData.category!,
        subcategory: templateData.subcategory!,
        tags: templateData.tags,
        canvas_data: templateData.canvas_data!,
        thumbnail_url: templateData.thumbnail_url,
        preview_images: templateData.preview_images,
        customizable_elements: templateData.customizable_elements,
        color_palettes: templateData.color_palettes,
        font_suggestions: templateData.font_suggestions,
        dimensions: templateData.dimensions!,
        aspect_ratio: templateData.aspect_ratio,
        orientation: templateData.orientation,
        difficulty_level: templateData.difficulty_level || DifficultyLevel.BEGINNER,
        license_type: templateData.license_type || LicenseType.FREE,
        license_details: templateData.license_details,
        is_public: templateData.is_public !== false
      };

      const result = await createTemplate(request);
      
      if (onSave) {
        onSave(result);
      }

    } catch (error) {
      console.error('Failed to create template:', error);
      // Handle error
    } finally {
      setIsSubmitting(false);
    }
  }, [templateData, steps, validateStep, createTemplate, onSave]);

  // Get available subcategories
  const availableSubcategories = templateData.category 
    ? Object.values(TemplateSubcategory).filter(subcat => {
        // Simple category matching logic
        return subcat.includes(templateData.category?.split('_')[0].toLowerCase() || '');
      })
    : [];

  // Render step content
  const renderStepContent = () => {
    const step = steps[currentStep];

    switch (step.id) {
      case 'basic':
        return (
          <div className=\"space-y-6\">
            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                템플릿 이름 *
              </label>
              <Input
                value={templateData.name || ''}
                onChange={(e) => handleFieldChange('name', e.target.value)}
                placeholder=\"예: 모던 비즈니스 카드 템플릿\"
                error={validationErrors.find(e => e.field === 'name')?.message}
              />
            </div>

            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                카테고리 *
              </label>
              <Select
                value={templateData.category}
                onValueChange={(value) => {
                  handleFieldChange('category', value);
                  handleFieldChange('subcategory', undefined); // Reset subcategory
                }}
                error={validationErrors.find(e => e.field === 'category')?.message}
              >
                {Object.values(TemplateCategory).map(category => (
                  <Select.Option key={category} value={category}>
                    {CATEGORY_LABELS[category]}
                  </Select.Option>
                ))}
              </Select>
            </div>

            {availableSubcategories.length > 0 && (
              <div>
                <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                  세부 카테고리
                </label>
                <Select
                  value={templateData.subcategory}
                  onValueChange={(value) => handleFieldChange('subcategory', value)}
                >
                  <Select.Option value={undefined}>선택하지 않음</Select.Option>
                  {availableSubcategories.map(subcategory => (
                    <Select.Option key={subcategory} value={subcategory}>
                      {SUBCATEGORY_LABELS[subcategory]}
                    </Select.Option>
                  ))}
                </Select>
              </div>
            )}

            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                설명
              </label>
              <Textarea
                value={templateData.description || ''}
                onChange={(e) => handleFieldChange('description', e.target.value)}
                placeholder=\"템플릿에 대한 자세한 설명을 입력하세요...\"
                rows={4}
                error={validationErrors.find(e => e.field === 'description')?.message}
              />
              <div className=\"text-xs text-gray-500 mt-1\">
                {(templateData.description || '').length} / 1000자
              </div>
            </div>

            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                난이도
              </label>
              <Select
                value={templateData.difficulty_level}
                onValueChange={(value) => handleFieldChange('difficulty_level', value)}
              >
                {Object.values(DifficultyLevel).map(level => (
                  <Select.Option key={level} value={level}>
                    {DIFFICULTY_LABELS[level]}
                  </Select.Option>
                ))}
              </Select>
            </div>
          </div>
        );

      case 'categorization':
        return (
          <div className=\"space-y-6\">
            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                태그 *
              </label>
              <TagInput
                value={templateData.tags || []}
                onChange={(tags) => handleFieldChange('tags', tags)}
                placeholder=\"태그 입력 후 Enter (예: 모던, 미니멀, 비즈니스)\"
                error={validationErrors.find(e => e.field === 'tags')?.message}
              />
              <div className=\"text-xs text-gray-500 mt-1\">
                템플릿을 쉽게 찾을 수 있도록 관련 태그를 추가하세요 (최대 10개)
              </div>
            </div>

            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                검색 키워드
              </label>
              <TagInput
                value={templateData.keywords || []}
                onChange={(keywords) => handleFieldChange('keywords', keywords)}
                placeholder=\"검색 키워드 입력 (선택사항)\"
              />
              <div className=\"text-xs text-gray-500 mt-1\">
                검색 시 더 잘 노출되도록 관련 키워드를 추가하세요
              </div>
            </div>

            {/* Auto-analysis results */}
            {analysisResults && (
              <Card className=\"bg-blue-50 border-blue-200\">
                <div className=\"flex items-start gap-3\">
                  <Sparkles className=\"w-5 h-5 text-blue-600 mt-0.5\" />
                  <div className=\"flex-1\">
                    <h4 className=\"text-sm font-medium text-blue-900 mb-2\">
                      자동 분석 결과
                    </h4>
                    <div className=\"space-y-2 text-sm text-blue-800\">
                      {analysisResults.keywords && analysisResults.keywords.length > 0 && (
                        <div>
                          <span className=\"font-medium\">추천 키워드: </span>
                          {analysisResults.keywords.slice(0, 5).join(', ')}
                        </div>
                      )}
                      <div>
                        <span className=\"font-medium\">복잡도: </span>
                        {analysisResults.complexity_score || 0}/100
                      </div>
                      <div>
                        <span className=\"font-medium\">예상 편집 시간: </span>
                        {analysisResults.estimated_edit_time || 0}분
                      </div>
                    </div>
                    <Button
                      variant=\"ghost\"
                      size=\"sm\"
                      className=\"mt-2 text-blue-700 hover:text-blue-800\"
                      onClick={() => setAutoAnalysis(!autoAnalysis)}
                    >
                      {autoAnalysis ? '자동 분석 끄기' : '자동 분석 켜기'}
                    </Button>
                  </div>
                </div>
              </Card>
            )}
          </div>
        );

      case 'design':
        return (
          <div className=\"space-y-6\">
            <div>
              <div className=\"flex items-center justify-between mb-4\">
                <label className=\"block text-sm font-medium text-gray-700\">
                  색상 팔레트
                </label>
                <Button
                  variant=\"outline\"
                  size=\"sm\"
                  onClick={handleAddColorPalette}
                >
                  팔레트 추가
                </Button>
              </div>

              {templateData.color_palettes && templateData.color_palettes.length > 0 ? (
                <div className=\"space-y-4\">
                  {templateData.color_palettes.map((palette, index) => (
                    <Card key={index} className=\"p-4\">
                      <div className=\"flex items-center justify-between mb-3\">
                        <Input
                          value={palette.name}
                          onChange={(e) => handleUpdateColorPalette(index, { ...palette, name: e.target.value })}
                          placeholder=\"팔레트 이름\"
                          className=\"flex-1 mr-3\"
                        />
                        <Button
                          variant=\"ghost\"
                          size=\"sm\"
                          onClick={() => handleRemoveColorPalette(index)}
                          className=\"text-red-600 hover:text-red-700\"
                        >
                          <X className=\"w-4 h-4\" />
                        </Button>
                      </div>
                      
                      <div className=\"flex gap-2 mb-3\">
                        {palette.colors.map((color, colorIndex) => (
                          <button
                            key={colorIndex}
                            className=\"w-12 h-12 rounded-lg border-2 border-gray-200\"
                            style={{ backgroundColor: color }}
                            onClick={() => {
                              // TODO: Open color picker
                            }}
                          />
                        ))}
                      </div>
                      
                      <Textarea
                        value={palette.description || ''}
                        onChange={(e) => handleUpdateColorPalette(index, { ...palette, description: e.target.value })}
                        placeholder=\"팔레트 설명 (선택사항)\"
                        rows={2}
                      />
                    </Card>
                  ))}
                </div>
              ) : (
                <div className=\"text-center py-8 text-gray-500\">
                  <Palette className=\"w-8 h-8 mx-auto mb-2\" />
                  <p className=\"text-sm\">색상 팔레트를 추가하여 사용자가 쉽게 커스터마이징할 수 있도록 하세요</p>
                </div>
              )}
            </div>

            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                추천 폰트
              </label>
              <TagInput
                value={templateData.font_suggestions || []}
                onChange={(fonts) => handleFieldChange('font_suggestions', fonts)}
                placeholder=\"폰트명 입력 (예: Noto Sans KR, Arial)\"
              />
              <div className=\"text-xs text-gray-500 mt-1\">
                템플릿에 어울리는 폰트를 추천해주세요
              </div>
            </div>
          </div>
        );

      case 'media':
        return (
          <div className=\"space-y-6\">
            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                썸네일 이미지
              </label>
              <FileUpload
                onUpload={handleThumbnailUpload}
                accept=\"image/*\"
                maxSize={5 * 1024 * 1024} // 5MB
                className=\"w-full\"
              />
              <div className=\"text-xs text-gray-500 mt-1\">
                권장 크기: 400×300px, 최대 5MB (JPG, PNG, WebP)
              </div>
              
              {thumbnailFile && (
                <div className=\"mt-3\">
                  <img
                    src={URL.createObjectURL(thumbnailFile)}
                    alt=\"Thumbnail preview\"
                    className=\"w-32 h-24 object-cover rounded-lg border border-gray-200\"
                  />
                </div>
              )}
            </div>

            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                미리보기 이미지 (선택사항)
              </label>
              <FileUpload
                onUpload={handlePreviewImagesUpload}
                accept=\"image/*\"
                multiple
                maxSize={10 * 1024 * 1024} // 10MB total
                className=\"w-full\"
              />
              <div className=\"text-xs text-gray-500 mt-1\">
                템플릿의 다양한 상태나 사용 예시를 보여주는 추가 이미지
              </div>
              
              {previewImages.length > 0 && (
                <div className=\"mt-3 grid grid-cols-3 gap-2\">
                  {previewImages.map((file, index) => (
                    <img
                      key={index}
                      src={URL.createObjectURL(file)}
                      alt={`Preview ${index + 1}`}
                      className=\"w-full h-24 object-cover rounded-lg border border-gray-200\"
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      case 'settings':
        return (
          <div className=\"space-y-6\">
            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                라이선스 유형
              </label>
              <Select
                value={templateData.license_type}
                onValueChange={(value) => handleFieldChange('license_type', value)}
              >
                {Object.values(LicenseType).map(license => (
                  <Select.Option key={license} value={license}>
                    <div className=\"flex items-center gap-2\">
                      {license === LicenseType.FREE ? (
                        <Unlock className=\"w-4 h-4 text-green-500\" />
                      ) : (
                        <Lock className=\"w-4 h-4 text-orange-500\" />
                      )}
                      {LICENSE_LABELS[license]}
                    </div>
                  </Select.Option>
                ))}
              </Select>
            </div>

            <div>
              <div className=\"flex items-center space-x-3\">
                <Checkbox
                  checked={templateData.is_public !== false}
                  onChange={(checked) => handleFieldChange('is_public', checked)}
                />
                <div className=\"flex-1\">
                  <label className=\"text-sm font-medium text-gray-700\">
                    공개 템플릿으로 등록
                  </label>
                  <p className=\"text-xs text-gray-500\">
                    다른 사용자들이 이 템플릿을 검색하고 사용할 수 있습니다
                  </p>
                </div>
              </div>
            </div>

            {templateData.is_public && (
              <Card className=\"bg-yellow-50 border-yellow-200\">
                <div className=\"flex items-start gap-3\">
                  <Crown className=\"w-5 h-5 text-yellow-600 mt-0.5\" />
                  <div className=\"flex-1\">
                    <h4 className=\"text-sm font-medium text-yellow-900 mb-1\">
                      공개 템플릿 등록
                    </h4>
                    <p className=\"text-sm text-yellow-800\">
                      공개 템플릿으로 등록하시면 AIPortal 커뮤니티에서 여러분의 창작물을 
                      공유하고 다른 사용자들의 피드백을 받을 수 있습니다.
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {/* Canvas Data Preview */}
            <div>
              <label className=\"block text-sm font-medium text-gray-700 mb-2\">
                Canvas 데이터
              </label>
              <Card className=\"p-4 bg-gray-50\">
                <div className=\"flex items-center justify-between mb-2\">
                  <span className=\"text-sm font-medium text-gray-700\">
                    데이터 크기: {JSON.stringify(templateData.canvas_data).length} bytes
                  </span>
                  <Button
                    variant=\"outline\"
                    size=\"sm\"
                    onClick={() => setShowPreview(!showPreview)}
                  >
                    <Eye className=\"w-4 h-4 mr-2\" />
                    {showPreview ? '숨기기' : '미리보기'}
                  </Button>
                </div>
                <div className=\"text-sm text-gray-600 mb-2\">
                  치수: {templateData.dimensions?.width} × {templateData.dimensions?.height}px
                </div>
                
                {showPreview && (
                  <pre className=\"text-xs text-gray-600 bg-white p-3 rounded border max-h-40 overflow-auto\">
                    {JSON.stringify(templateData.canvas_data, null, 2)}
                  </pre>
                )}
              </Card>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={cn('flex h-full bg-white', className)}>
      {/* Steps Sidebar */}
      <div className=\"flex-none w-80 p-6 border-r border-gray-200 bg-gray-50\">
        <div className=\"sticky top-6\">
          <h2 className=\"text-xl font-semibold text-gray-900 mb-6\">
            템플릿 만들기
          </h2>

          <div className=\"space-y-3\">
            {steps.map((step, index) => (
              <button
                key={step.id}
                onClick={() => handleStepChange(index)}
                disabled={isSubmitting}
                className={cn(
                  'w-full flex items-start gap-3 p-4 rounded-lg text-left transition-colors',
                  index === currentStep
                    ? 'bg-blue-100 border-2 border-blue-300'
                    : step.completed
                      ? 'bg-green-50 border border-green-200 hover:bg-green-100'
                      : 'bg-white border border-gray-200 hover:bg-gray-50'
                )}
              >
                <div className={cn(
                  'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
                  index === currentStep
                    ? 'bg-blue-600 text-white'
                    : step.completed
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-300 text-gray-600'
                )}>
                  {step.completed ? (
                    <Check className=\"w-4 h-4\" />
                  ) : (
                    <span className=\"text-sm font-medium\">{index + 1}</span>
                  )}
                </div>
                
                <div className=\"flex-1 min-w-0\">
                  <div className=\"flex items-center gap-2\">
                    {step.icon}
                    <h3 className={cn(
                      'font-medium',
                      index === currentStep
                        ? 'text-blue-900'
                        : step.completed
                          ? 'text-green-900'
                          : 'text-gray-700'
                    )}>
                      {step.title}
                    </h3>
                    {step.optional && (
                      <Badge variant=\"secondary\" size=\"sm\">
                        선택
                      </Badge>
                    )}
                  </div>
                  <p className={cn(
                    'text-xs mt-1',
                    index === currentStep
                      ? 'text-blue-700'
                      : step.completed
                        ? 'text-green-700'
                        : 'text-gray-500'
                  )}>
                    {step.description}
                  </p>
                </div>
              </button>
            ))}
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <Card className=\"mt-6 p-4 bg-red-50 border-red-200\">
              <div className=\"flex items-start gap-3\">
                <AlertTriangle className=\"w-5 h-5 text-red-600 mt-0.5\" />
                <div className=\"flex-1\">
                  <h4 className=\"text-sm font-medium text-red-900 mb-2\">
                    입력 오류
                  </h4>
                  <ul className=\"text-sm text-red-800 space-y-1\">
                    {validationErrors.map((error, index) => (
                      <li key={index}>• {error.message}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className=\"flex-1 flex flex-col\">
        {/* Header */}
        <div className=\"flex-none p-6 border-b border-gray-200\">
          <div className=\"flex items-center justify-between\">
            <div>
              <h1 className=\"text-2xl font-semibold text-gray-900\">
                {steps[currentStep].title}
              </h1>
              <p className=\"text-gray-600 mt-1\">
                {steps[currentStep].description}
              </p>
            </div>
            
            <div className=\"flex items-center gap-3\">
              <span className=\"text-sm text-gray-500\">
                {currentStep + 1} / {steps.length}
              </span>
              
              {onCancel && (
                <Button variant=\"ghost\" onClick={onCancel}>
                  취소
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Step Content */}
        <div className=\"flex-1 overflow-y-auto p-6\">
          <div className=\"max-w-2xl\">
            <AnimatePresence mode=\"wait\">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                {renderStepContent()}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Footer */}
        <div className=\"flex-none p-6 border-t border-gray-200\">
          <div className=\"flex items-center justify-between\">
            <Button
              variant=\"outline\"
              onClick={() => handleStepChange(Math.max(0, currentStep - 1))}
              disabled={currentStep === 0 || isSubmitting}
            >
              이전
            </Button>

            <div className=\"flex items-center gap-3\">
              {currentStep === steps.length - 1 ? (
                <Button
                  variant=\"primary\"
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className=\"min-w-32\"
                >
                  {isSubmitting ? (
                    <>
                      <LoadingSpinner size=\"sm\" className=\"mr-2\" />
                      생성 중...
                    </>
                  ) : (
                    <>
                      <Save className=\"w-4 h-4 mr-2\" />
                      템플릿 생성
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  variant=\"primary\"
                  onClick={() => handleStepChange(currentStep + 1)}
                  disabled={isSubmitting}
                >
                  다음
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemplateCreator;