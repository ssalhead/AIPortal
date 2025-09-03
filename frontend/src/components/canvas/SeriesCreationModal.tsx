/**
 * 시리즈 생성 모달 컴포넌트
 * 
 * 새로운 이미지 시리즈를 생성하기 위한 고급 설정 모달
 * - 시리즈 타입 선택
 * - 템플릿 기반 생성
 * - 프롬프트 체이닝 설정
 * - 캐릭터 일관성 관리
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  ChevronLeft,
  ChevronRight,
  Wand2,
  Plus,
  Trash2,
  Copy,
  Sparkles,
  Settings,
  Users,
  Palette,
  Grid3X3,
  BookOpen,
  Camera,
  Briefcase,
  Film,
  Cog,
  Star,
  Info
} from 'lucide-react';

import {
  SeriesType,
  SERIES_TYPE_CONFIGS,
  SeriesTemplate,
  SeriesCreationRequest
} from '../../types/imageSeries';
import { imageSeriesService } from '../../services/imageSeriesService';

interface SeriesCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSeriesCreated: (seriesId: string) => void;
  conversationId: string;
}

interface StepProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

const Step: React.FC<StepProps> = ({ title, description, children }) => (
  <div className="space-y-6">
    <div className="text-center">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
        {title}
      </h2>
      <p className="text-gray-600 dark:text-gray-400">
        {description}
      </p>
    </div>
    {children}
  </div>
);

const SeriesCreationModal: React.FC<SeriesCreationModalProps> = ({
  isOpen,
  onClose,
  onSeriesCreated,
  conversationId
}) => {
  // 단계 관리
  const [currentStep, setCurrentStep] = useState(0);
  const [isCreating, setIsCreating] = useState(false);

  // 폼 데이터
  const [formData, setFormData] = useState<Partial<SeriesCreationRequest>>({
    title: '',
    series_type: 'webtoon',
    target_count: 4,
    base_style: 'realistic',
    consistency_prompt: '',
    base_prompts: [''],
    character_descriptions: {}
  });

  // 템플릿 관련
  const [availableTemplates, setAvailableTemplates] = useState<SeriesTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<SeriesTemplate | null>(null);

  const steps = [
    {
      title: '시리즈 타입 선택',
      description: '어떤 종류의 이미지 시리즈를 만들고 싶으신가요?'
    },
    {
      title: '기본 설정',
      description: '시리즈의 제목과 기본 설정을 입력해주세요'
    },
    {
      title: '프롬프트 설정',
      description: '각 이미지에 대한 프롬프트를 설정하세요'
    },
    {
      title: '일관성 설정',
      description: '캐릭터와 스타일의 일관성을 위한 설정입니다'
    },
    {
      title: '최종 확인',
      description: '설정을 확인하고 시리즈를 생성하세요'
    }
  ];

  // 템플릿 로드
  useEffect(() => {
    if (isOpen && formData.series_type) {
      loadTemplates();
    }
  }, [isOpen, formData.series_type]);

  // 모달 리셋
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
      setFormData({
        title: '',
        series_type: 'webtoon',
        target_count: 4,
        base_style: 'realistic',
        consistency_prompt: '',
        base_prompts: [''],
        character_descriptions: {}
      });
      setSelectedTemplate(null);
    }
  }, [isOpen]);

  const loadTemplates = async () => {
    try {
      const templates = await imageSeriesService.getTemplates(formData.series_type);
      setAvailableTemplates(templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const handleSeriesTypeSelect = (type: SeriesType) => {
    const config = SERIES_TYPE_CONFIGS[type];
    setFormData(prev => ({
      ...prev,
      series_type: type,
      target_count: config.recommended_count[0] || 4
    }));
  };

  const handleTemplateSelect = (template: SeriesTemplate | null) => {
    setSelectedTemplate(template);
    if (template) {
      setFormData(prev => ({
        ...prev,
        template_id: template.id,
        target_count: template.default_target_count,
        base_style: template.recommended_style
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        template_id: undefined
      }));
    }
  };

  const handlePromptChange = (index: number, value: string) => {
    const newPrompts = [...(formData.base_prompts || [])];
    newPrompts[index] = value;
    setFormData(prev => ({
      ...prev,
      base_prompts: newPrompts
    }));
  };

  const addPrompt = () => {
    setFormData(prev => ({
      ...prev,
      base_prompts: [...(prev.base_prompts || []), '']
    }));
  };

  const removePrompt = (index: number) => {
    if ((formData.base_prompts?.length || 0) <= 1) return;
    const newPrompts = formData.base_prompts?.filter((_, i) => i !== index) || [];
    setFormData(prev => ({
      ...prev,
      base_prompts: newPrompts,
      target_count: newPrompts.length
    }));
  };

  const handleCharacterChange = (name: string, description: string) => {
    setFormData(prev => ({
      ...prev,
      character_descriptions: {
        ...prev.character_descriptions,
        [name]: description
      }
    }));
  };

  const removeCharacter = (name: string) => {
    const newDescriptions = { ...formData.character_descriptions };
    delete newDescriptions[name];
    setFormData(prev => ({
      ...prev,
      character_descriptions: newDescriptions
    }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0: return !!formData.series_type;
      case 1: return !!formData.title && formData.target_count > 0;
      case 2: return (formData.base_prompts || []).every(p => p.trim().length > 0);
      case 3: return true; // 선택적 단계
      case 4: return true;
      default: return false;
    }
  };

  const handleCreate = async () => {
    if (!formData.title || !formData.series_type || !formData.base_prompts) return;

    setIsCreating(true);
    try {
      const series = await imageSeriesService.createSeries({
        title: formData.title,
        series_type: formData.series_type,
        target_count: formData.target_count || 4,
        base_style: formData.base_style || 'realistic',
        consistency_prompt: formData.consistency_prompt,
        template_id: formData.template_id,
        base_prompts: formData.base_prompts,
        character_descriptions: formData.character_descriptions
      });

      onSeriesCreated(series.id);
      onClose();
    } catch (error) {
      console.error('Failed to create series:', error);
      alert('시리즈 생성에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setIsCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                이미지 시리즈 만들기
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                단계 {currentStep + 1} / {steps.length}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* 진행 표시 */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            {steps.map((step, index) => (
              <React.Fragment key={index}>
                <div className="flex items-center">
                  <div
                    className={`
                      w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                      ${index <= currentStep
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                      }
                    `}
                  >
                    {index + 1}
                  </div>
                  <span className="ml-2 text-sm text-gray-600 dark:text-gray-400 hidden md:inline">
                    {step.title}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`
                      flex-1 h-1 mx-4
                      ${index < currentStep ? 'bg-blue-500' : 'bg-gray-200 dark:bg-gray-700'}
                    `}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* 콘텐츠 */}
        <div className="p-6 max-h-96 overflow-y-auto">
          {/* Step 0: 시리즈 타입 선택 */}
          {currentStep === 0 && (
            <Step title={steps[0].title} description={steps[0].description}>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(SERIES_TYPE_CONFIGS).map(([type, config]) => (
                  <button
                    key={type}
                    onClick={() => handleSeriesTypeSelect(type as SeriesType)}
                    className={`
                      p-4 rounded-xl border-2 text-left transition-all hover:shadow-md
                      ${formData.series_type === type
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }
                    `}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`p-2 ${config.color} rounded-lg`}>
                        <span className="text-lg">{config.icon}</span>
                      </div>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                        {config.name}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      {config.description}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {config.recommended_count.map(count => (
                        <span
                          key={count}
                          className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-xs rounded"
                        >
                          {count}개
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>

              {formData.series_type && (
                <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Info className="w-4 h-4 text-blue-500" />
                    <span className="font-medium text-blue-900 dark:text-blue-100">
                      {SERIES_TYPE_CONFIGS[formData.series_type as SeriesType].name} 선택됨
                    </span>
                  </div>
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    추천 개수: {SERIES_TYPE_CONFIGS[formData.series_type as SeriesType].recommended_count.join(', ')}개
                  </p>
                </div>
              )}
            </Step>
          )}

          {/* Step 1: 기본 설정 */}
          {currentStep === 1 && (
            <Step title={steps[1].title} description={steps[1].description}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 기본 정보 */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      시리즈 제목 *
                    </label>
                    <input
                      type="text"
                      value={formData.title || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="예: 판타지 모험 시리즈"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      목표 이미지 개수
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      value={formData.target_count || 4}
                      onChange={(e) => setFormData(prev => ({ ...prev, target_count: parseInt(e.target.value) || 4 }))}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      기본 스타일
                    </label>
                    <select
                      value={formData.base_style || 'realistic'}
                      onChange={(e) => setFormData(prev => ({ ...prev, base_style: e.target.value }))}
                      className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    >
                      <option value="realistic">사실적</option>
                      <option value="artistic">예술적</option>
                      <option value="cartoon">만화</option>
                      <option value="abstract">추상적</option>
                      <option value="3d">3D</option>
                      <option value="anime">애니메이션</option>
                    </select>
                  </div>
                </div>

                {/* 템플릿 선택 */}
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                    템플릿 선택 (선택사항)
                  </label>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    <button
                      onClick={() => handleTemplateSelect(null)}
                      className={`
                        w-full p-3 text-left rounded-lg border transition-colors
                        ${!selectedTemplate
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                        }
                      `}
                    >
                      <div className="font-medium text-gray-900 dark:text-gray-100">
                        기본 설정 사용
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        템플릿 없이 직접 설정
                      </div>
                    </button>

                    {availableTemplates.map(template => (
                      <button
                        key={template.id}
                        onClick={() => handleTemplateSelect(template)}
                        className={`
                          w-full p-3 text-left rounded-lg border transition-colors
                          ${selectedTemplate?.id === template.id
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                          }
                        `}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="font-medium text-gray-900 dark:text-gray-100">
                            {template.name}
                          </div>
                          <div className="flex items-center gap-1">
                            <Star className="w-3 h-3 text-yellow-400" />
                            <span className="text-xs text-gray-500">{template.rating}</span>
                          </div>
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {template.description}
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          사용 횟수: {template.usage_count}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </Step>
          )}

          {/* Step 2: 프롬프트 설정 */}
          {currentStep === 2 && (
            <Step title={steps[2].title} description={steps[2].description}>
              <div className="space-y-4">
                {formData.base_prompts?.map((prompt, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 mt-1">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <textarea
                        value={prompt}
                        onChange={(e) => handlePromptChange(index, e.target.value)}
                        className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
                        rows={3}
                        placeholder={`${index + 1}번째 이미지에 대한 설명을 입력하세요...`}
                      />
                    </div>
                    {(formData.base_prompts?.length || 0) > 1 && (
                      <button
                        onClick={() => removePrompt(index)}
                        className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg flex-shrink-0"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}

                <button
                  onClick={addPrompt}
                  className="w-full p-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-400 hover:border-blue-500 hover:text-blue-500 transition-colors flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  프롬프트 추가
                </button>
              </div>
            </Step>
          )}

          {/* Step 3: 일관성 설정 */}
          {currentStep === 3 && (
            <Step title={steps[3].title} description={steps[3].description}>
              <div className="space-y-6">
                {/* 공통 프롬프트 */}
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                    일관성 유지 프롬프트 (선택사항)
                  </label>
                  <textarea
                    value={formData.consistency_prompt || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, consistency_prompt: e.target.value }))}
                    className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
                    rows={3}
                    placeholder="모든 이미지에 공통으로 적용할 스타일이나 설정을 입력하세요..."
                  />
                </div>

                {/* 캐릭터 설명 */}
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                    캐릭터 설명 (선택사항)
                  </label>
                  <div className="space-y-3">
                    {Object.entries(formData.character_descriptions || {}).map(([name, description]) => (
                      <div key={name} className="flex items-start gap-3">
                        <input
                          type="text"
                          value={name}
                          onChange={(e) => {
                            const newName = e.target.value;
                            const newDescriptions = { ...formData.character_descriptions };
                            delete newDescriptions[name];
                            newDescriptions[newName] = description;
                            setFormData(prev => ({ ...prev, character_descriptions: newDescriptions }));
                          }}
                          className="w-32 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                          placeholder="캐릭터명"
                        />
                        <input
                          type="text"
                          value={description}
                          onChange={(e) => handleCharacterChange(name, e.target.value)}
                          className="flex-1 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                          placeholder="캐릭터 외모 설명"
                        />
                        <button
                          onClick={() => removeCharacter(name)}
                          className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => handleCharacterChange('캐릭터1', '')}
                      className="w-full p-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-400 hover:border-blue-500 hover:text-blue-500 transition-colors flex items-center justify-center gap-2"
                    >
                      <Users className="w-4 h-4" />
                      캐릭터 추가
                    </button>
                  </div>
                </div>
              </div>
            </Step>
          )}

          {/* Step 4: 최종 확인 */}
          {currentStep === 4 && (
            <Step title={steps[4].title} description={steps[4].description}>
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 space-y-4">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">시리즈 정보</h3>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    <p><strong>제목:</strong> {formData.title}</p>
                    <p><strong>타입:</strong> {SERIES_TYPE_CONFIGS[formData.series_type as SeriesType]?.name}</p>
                    <p><strong>이미지 개수:</strong> {formData.target_count}개</p>
                    <p><strong>스타일:</strong> {formData.base_style}</p>
                    {selectedTemplate && (
                      <p><strong>템플릿:</strong> {selectedTemplate.name}</p>
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">프롬프트 목록</h3>
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {formData.base_prompts?.map((prompt, index) => (
                      <div key={index} className="text-sm text-gray-600 dark:text-gray-400">
                        <strong>{index + 1}.</strong> {prompt || '(비어있음)'}
                      </div>
                    ))}
                  </div>
                </div>

                {formData.consistency_prompt && (
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">일관성 프롬프트</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {formData.consistency_prompt}
                    </p>
                  </div>
                )}

                {Object.keys(formData.character_descriptions || {}).length > 0 && (
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">캐릭터 설명</h3>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {Object.entries(formData.character_descriptions || {}).map(([name, desc]) => (
                        <p key={name}><strong>{name}:</strong> {desc}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Step>
          )}
        </div>

        {/* 푸터 */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg transition-colors
              ${currentStep === 0
                ? 'text-gray-400 cursor-not-allowed'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }
            `}
          >
            <ChevronLeft className="w-4 h-4" />
            이전
          </button>

          <div className="flex items-center gap-3">
            {currentStep === steps.length - 1 ? (
              <button
                onClick={handleCreate}
                disabled={!canProceed() || isCreating}
                className={`
                  flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-colors
                  ${canProceed() && !isCreating
                    ? 'bg-blue-500 text-white hover:bg-blue-600'
                    : 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                {isCreating ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    생성 중...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" />
                    시리즈 생성
                  </>
                )}
              </button>
            ) : (
              <button
                onClick={() => setCurrentStep(Math.min(steps.length - 1, currentStep + 1))}
                disabled={!canProceed()}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg transition-colors
                  ${canProceed()
                    ? 'bg-blue-500 text-white hover:bg-blue-600'
                    : 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                다음
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SeriesCreationModal;