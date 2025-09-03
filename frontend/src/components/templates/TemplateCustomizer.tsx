// Template Customizer Component
// AIPortal Canvas Template Library - 템플릿 커스터마이징 UI 컴포넌트

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Palette, Type, Image, Move, RotateCcw, Download,
  Play, Save, Share2, Eye, Settings, ChevronDown,
  ChevronUp, X, Check, AlertTriangle, Sparkles,
  Zap, Target, Layers, Sliders, Grid, Paintbrush2
} from 'lucide-react';

import {
  TemplateDetailResponse,
  ColorPalette,
  CustomizableElement,
  TemplateCustomizationSession
} from '../../types/template';

import { 
  TemplateCustomizationEngine, 
  ColorUtils, 
  FontManager,
  CustomizationUtils 
} from '../../services/TemplateCustomizationEngine';

import { cn } from '../../utils/cn';
import Button from '../ui/Button';
import ColorPicker from '../ui/ColorPicker';
import FontSelector from '../ui/FontSelector';
import Slider from '../ui/Slider';
import Tabs from '../ui/Tabs';
import Badge from '../ui/Badge';
import Tooltip from '../ui/Tooltip';
import LoadingSpinner from '../ui/LoadingSpinner';
import Modal from '../ui/Modal';

interface TemplateCustomizerProps {
  template: TemplateDetailResponse;
  onApply?: (canvasData: Record<string, any>, customizations: any) => void;
  onSave?: (preset: Record<string, any>) => void;
  onClose?: () => void;
  className?: string;
  showPreview?: boolean;
  previewSize?: 'sm' | 'md' | 'lg';
}

interface CustomizationTab {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
}

interface ColorHarmony {
  type: 'complementary' | 'triadic' | 'analogous' | 'monochromatic';
  label: string;
  description: string;
}

const TemplateCustomizer: React.FC<TemplateCustomizerProps> = ({
  template,
  onApply,
  onSave,
  onClose,
  className,
  showPreview = true,
  previewSize = 'md'
}) => {
  // State
  const [activeTab, setActiveTab] = useState('colors');
  const [engine, setEngine] = useState<TemplateCustomizationEngine | null>(null);
  const [currentCanvasData, setCurrentCanvasData] = useState(template.canvas_data);
  const [customizations, setCustomizations] = useState<any[]>([]);
  const [session, setSession] = useState<TemplateCustomizationSession | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [presetDescription, setPresetDescription] = useState('');

  // Customization states
  const [selectedColors, setSelectedColors] = useState<string[]>([]);
  const [selectedFont, setSelectedFont] = useState('');
  const [selectedImages, setSelectedImages] = useState<Record<string, string>>({});
  const [elementPositions, setElementPositions] = useState<Record<string, {x: number, y: number}>>({});

  // Refs
  const previewRef = useRef<HTMLDivElement>(null);

  // Initialize customization engine
  useEffect(() => {
    const customizationEngine = new TemplateCustomizationEngine(template);
    setEngine(customizationEngine);

    const state = customizationEngine.getCurrentState();
    setCurrentCanvasData(state.canvas_data);
    setSession(state.session);

    // Initialize customizable colors
    if (template.color_palettes && template.color_palettes.length > 0) {
      setSelectedColors(template.color_palettes[0].colors);
    }

    // Initialize font
    if (template.font_suggestions && template.font_suggestions.length > 0) {
      setSelectedFont(template.font_suggestions[0]);
    }
  }, [template]);

  // Tabs configuration
  const tabs: CustomizationTab[] = [
    {
      id: 'colors',
      label: '색상',
      icon: <Palette className=\"w-4 h-4\" />,
      badge: selectedColors.length
    },
    {
      id: 'text',
      label: '텍스트',
      icon: <Type className=\"w-4 h-4\" />
    },
    {
      id: 'images',
      label: '이미지',
      icon: <Image className=\"w-4 h-4\" />,
      badge: Object.keys(selectedImages).length
    },
    {
      id: 'layout',
      label: '레이아웃',
      icon: <Move className=\"w-4 h-4\" />
    },
    {
      id: 'effects',
      label: '효과',
      icon: <Sparkles className=\"w-4 h-4\" />
    }
  ];

  // Color harmonies
  const colorHarmonies: ColorHarmony[] = [
    {
      type: 'complementary',
      label: '보색',
      description: '대비가 강한 색상 조합'
    },
    {
      type: 'triadic',
      label: '삼각형',
      description: '균형잡힌 3색 조합'
    },
    {
      type: 'analogous',
      label: '유사색',
      description: '부드러운 색상 조합'
    },
    {
      type: 'monochromatic',
      label: '단색',
      description: '한 색상의 다양한 톤'
    }
  ];

  // Handlers
  const handleColorPaletteChange = useCallback((newPalette: ColorPalette) => {
    if (!engine) return;

    try {
      const newCanvasData = engine.changeColorPalette(newPalette);
      setCurrentCanvasData(newCanvasData);
      setSelectedColors(newPalette.colors);
      setHasChanges(true);

      const state = engine.getCurrentState();
      setCustomizations(state.customizations);
      setSession(state.session);
    } catch (error) {
      console.error('Failed to change color palette:', error);
    }
  }, [engine]);

  const handleColorHarmonyGenerate = useCallback((baseColor: string, harmonyType: ColorHarmony['type']) => {
    if (!engine) return;

    const harmonicColors = engine.generateColorHarmony(baseColor, harmonyType);
    const newPalette: ColorPalette = {
      name: `${harmonyType} 조화`,
      colors: harmonicColors,
      description: colorHarmonies.find(h => h.type === harmonyType)?.description
    };

    handleColorPaletteChange(newPalette);
  }, [engine, colorHarmonies, handleColorPaletteChange]);

  const handleFontChange = useCallback((fontFamily: string, global: boolean = false) => {
    if (!engine) return;

    try {
      const newCanvasData = global 
        ? engine.changeAllFonts(fontFamily)
        : engine.changeFont('selected-text', fontFamily); // TODO: 선택된 텍스트 요소

      setCurrentCanvasData(newCanvasData);
      setSelectedFont(fontFamily);
      setHasChanges(true);

      const state = engine.getCurrentState();
      setCustomizations(state.customizations);
      setSession(state.session);
    } catch (error) {
      console.error('Failed to change font:', error);
    }
  }, [engine]);

  const handleUndo = useCallback(() => {
    if (!engine) return;

    const newCanvasData = engine.undo();
    if (newCanvasData) {
      setCurrentCanvasData(newCanvasData);
      
      const state = engine.getCurrentState();
      setCustomizations(state.customizations);
      setSession(state.session);
      setHasChanges(state.customizations.length > 0);
    }
  }, [engine]);

  const handleReset = useCallback(() => {
    if (!engine) return;

    const newCanvasData = engine.reset();
    setCurrentCanvasData(newCanvasData);
    setHasChanges(false);

    const state = engine.getCurrentState();
    setCustomizations(state.customizations);
    setSession(state.session);

    // Reset UI states
    if (template.color_palettes && template.color_palettes.length > 0) {
      setSelectedColors(template.color_palettes[0].colors);
    }
    if (template.font_suggestions && template.font_suggestions.length > 0) {
      setSelectedFont(template.font_suggestions[0]);
    }
    setSelectedImages({});
    setElementPositions({});
  }, [engine, template]);

  const handleApply = useCallback(() => {
    if (!engine || !onApply) return;

    const exportData = engine.exportForCanvas();
    const state = engine.getCurrentState();
    
    onApply(exportData, state.customizations);
  }, [engine, onApply]);

  const handleSavePreset = useCallback(() => {
    if (!engine || !presetName.trim()) return;

    const preset = engine.createPreset(presetName, presetDescription);
    
    if (onSave) {
      onSave(preset);
    }
    
    setShowSaveModal(false);
    setPresetName('');
    setPresetDescription('');
  }, [engine, presetName, presetDescription, onSave]);

  // Render methods
  const renderColorCustomization = () => (
    <div className=\"space-y-6\">
      {/* Current Color Palette */}
      <div>
        <h4 className=\"text-sm font-medium text-gray-900 mb-3\">현재 색상 팔레트</h4>
        <div className=\"flex gap-2 mb-4\">
          {selectedColors.map((color, index) => (
            <button
              key={index}
              className=\"w-12 h-12 rounded-lg border-2 border-gray-200 shadow-sm transition-transform hover:scale-105\"
              style={{ backgroundColor: color }}
              onClick={() => {
                // TODO: 개별 색상 편집
              }}
            />
          ))}
        </div>
        <Button
          variant=\"outline\"
          size=\"sm\"
          onClick={() => {
            // TODO: 색상 추가
          }}
        >
          색상 추가
        </Button>
      </div>

      {/* Color Harmony Generator */}
      <div>
        <h4 className=\"text-sm font-medium text-gray-900 mb-3\">색상 조화 생성</h4>
        <div className=\"grid grid-cols-2 gap-2\">
          {colorHarmonies.map((harmony) => (
            <Button
              key={harmony.type}
              variant=\"outline\"
              size=\"sm\"
              onClick={() => handleColorHarmonyGenerate(selectedColors[0] || '#007bff', harmony.type)}
              className=\"flex flex-col items-start p-3 h-auto\"
            >
              <span className=\"font-medium\">{harmony.label}</span>
              <span className=\"text-xs text-gray-600 mt-1\">{harmony.description}</span>
            </Button>
          ))}
        </div>
      </div>

      {/* Predefined Palettes */}
      {template.color_palettes && template.color_palettes.length > 0 && (
        <div>
          <h4 className=\"text-sm font-medium text-gray-900 mb-3\">추천 팔레트</h4>
          <div className=\"space-y-3\">
            {template.color_palettes.map((palette, index) => (
              <button
                key={index}
                onClick={() => handleColorPaletteChange(palette)}
                className=\"w-full p-3 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors text-left\"
              >
                <div className=\"flex items-center gap-3 mb-2\">
                  <div className=\"flex gap-1\">
                    {palette.colors.slice(0, 5).map((color, colorIndex) => (
                      <div
                        key={colorIndex}
                        className=\"w-6 h-6 rounded border border-gray-200\"
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>
                  <span className=\"font-medium text-sm\">{palette.name}</span>
                </div>
                {palette.description && (
                  <p className=\"text-xs text-gray-600\">{palette.description}</p>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderTextCustomization = () => (
    <div className=\"space-y-6\">
      {/* Font Selection */}
      <div>
        <h4 className=\"text-sm font-medium text-gray-900 mb-3\">폰트 선택</h4>
        <FontSelector
          value={selectedFont}
          onChange={handleFontChange}
          fonts={FontManager.getAllFonts()}
        />
        
        {selectedFont && (
          <div className=\"mt-3 p-3 bg-gray-50 rounded-lg\">
            <p className=\"text-sm\" style={{ fontFamily: selectedFont }}>
              이 폰트로 미리보기 텍스트를 확인해보세요.
            </p>
          </div>
        )}
      </div>

      {/* Font Suggestions */}
      {template.font_suggestions && template.font_suggestions.length > 0 && (
        <div>
          <h4 className=\"text-sm font-medium text-gray-900 mb-3\">추천 폰트</h4>
          <div className=\"space-y-2\">
            {template.font_suggestions.map((font, index) => (
              <button
                key={index}
                onClick={() => handleFontChange(font, true)}
                className={cn(
                  'w-full p-3 border rounded-lg text-left transition-colors',
                  selectedFont === font
                    ? 'border-blue-300 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <div className=\"flex items-center justify-between\">
                  <span className=\"font-medium\" style={{ fontFamily: font }}>
                    {font}
                  </span>
                  {selectedFont === font && (
                    <Check className=\"w-4 h-4 text-blue-600\" />
                  )}
                </div>
                <p className=\"text-xs text-gray-600 mt-1\" style={{ fontFamily: font }}>
                  샘플 텍스트입니다
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Text Size Control */}
      <div>
        <h4 className=\"text-sm font-medium text-gray-900 mb-3\">글꼴 크기</h4>
        <Slider
          value={[16]}
          onValueChange={([value]) => {
            // TODO: 글꼴 크기 변경
          }}
          min={8}
          max={72}
          step={1}
          className=\"w-full\"
        />
        <div className=\"flex justify-between text-xs text-gray-500 mt-1\">
          <span>8px</span>
          <span>72px</span>
        </div>
      </div>

      {/* Global Font Actions */}
      <div className=\"pt-4 border-t border-gray-200\">
        <Button
          variant=\"outline\"
          size=\"sm\"
          onClick={() => {
            if (selectedFont) {
              handleFontChange(selectedFont, true);
            }
          }}
          className=\"w-full\"
        >
          <Type className=\"w-4 h-4 mr-2\" />
          모든 텍스트에 적용
        </Button>
      </div>
    </div>
  );

  const renderImageCustomization = () => (
    <div className=\"space-y-6\">
      <div>
        <h4 className=\"text-sm font-medium text-gray-900 mb-3\">이미지 교체</h4>
        <p className=\"text-sm text-gray-600 mb-4\">
          템플릿의 이미지를 원하는 이미지로 교체할 수 있습니다.
        </p>
        
        {/* TODO: 이미지 요소 목록 및 교체 UI */}
        <div className=\"text-center py-8 text-gray-500\">
          <Image className=\"w-8 h-8 mx-auto mb-2\" />
          <p className=\"text-sm\">이미지 교체 기능은 곧 제공됩니다</p>
        </div>
      </div>
    </div>
  );

  const renderLayoutCustomization = () => (
    <div className=\"space-y-6\">
      <div>
        <h4 className=\"text-sm font-medium text-gray-900 mb-3\">레이아웃 조정</h4>
        <p className=\"text-sm text-gray-600 mb-4\">
          요소들의 위치와 크기를 조정할 수 있습니다.
        </p>
        
        {/* TODO: 레이아웃 조정 UI */}
        <div className=\"text-center py-8 text-gray-500\">
          <Grid className=\"w-8 h-8 mx-auto mb-2\" />
          <p className=\"text-sm\">레이아웃 조정 기능은 곧 제공됩니다</p>
        </div>
      </div>
    </div>
  );

  const renderEffectsCustomization = () => (
    <div className=\"space-y-6\">
      <div>
        <h4 className=\"text-sm font-medium text-gray-900 mb-3\">시각 효과</h4>
        <p className=\"text-sm text-gray-600 mb-4\">
          그림자, 테두리, 투명도 등의 시각 효과를 추가할 수 있습니다.
        </p>
        
        {/* TODO: 효과 조정 UI */}
        <div className=\"text-center py-8 text-gray-500\">
          <Sparkles className=\"w-8 h-8 mx-auto mb-2\" />
          <p className=\"text-sm\">시각 효과 기능은 곧 제공됩니다</p>
        </div>
      </div>
    </div>
  );

  // Preview size classes
  const previewSizeClass = {
    sm: 'w-64 h-48',
    md: 'w-80 h-60', 
    lg: 'w-96 h-72'
  }[previewSize];

  return (
    <div className={cn('flex h-full bg-white', className)}>
      {/* Preview Panel */}
      {showPreview && (
        <div className=\"flex-none w-1/2 p-6 border-r border-gray-200\">
          <div className=\"sticky top-6\">
            <div className=\"flex items-center justify-between mb-4\">
              <h3 className=\"text-lg font-semibold text-gray-900\">미리보기</h3>
              <div className=\"flex items-center gap-2\">
                <Badge variant={hasChanges ? 'warning' : 'success'} size=\"sm\">
                  {hasChanges ? '수정됨' : '저장됨'}
                </Badge>
              </div>
            </div>

            {/* Preview Container */}
            <div className=\"relative bg-gray-50 rounded-lg p-4 mb-4\">
              <div 
                ref={previewRef}
                className={cn(
                  'mx-auto bg-white rounded shadow-sm overflow-hidden',
                  previewSizeClass
                )}
                style={{
                  aspectRatio: `${template.dimensions.width} / ${template.dimensions.height}`
                }}
              >
                {previewLoading ? (
                  <div className=\"flex items-center justify-center h-full\">
                    <LoadingSpinner size=\"md\" />
                  </div>
                ) : (
                  <div className=\"w-full h-full flex items-center justify-center text-gray-500\">
                    <div className=\"text-center\">
                      <Eye className=\"w-8 h-8 mx-auto mb-2\" />
                      <p className=\"text-sm\">템플릿 미리보기</p>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Preview Controls */}
              <div className=\"flex items-center justify-center gap-2\">
                <Button variant=\"outline\" size=\"sm\">
                  <Target className=\"w-4 h-4 mr-2\" />
                  실제 크기
                </Button>
                <Button variant=\"outline\" size=\"sm\">
                  <Layers className=\"w-4 h-4 mr-2\" />
                  레이어 보기
                </Button>
              </div>
            </div>

            {/* Action Buttons */}
            <div className=\"space-y-3\">
              <Button
                variant=\"primary\"
                size=\"sm\"
                className=\"w-full\"
                onClick={handleApply}
                disabled={!hasChanges}
              >
                <Play className=\"w-4 h-4 mr-2\" />
                템플릿 적용
              </Button>
              
              <div className=\"flex gap-2\">
                <Button
                  variant=\"outline\"
                  size=\"sm\"
                  className=\"flex-1\"
                  onClick={() => setShowSaveModal(true)}
                  disabled={!hasChanges}
                >
                  <Save className=\"w-4 h-4 mr-2\" />
                  프리셋 저장
                </Button>
                
                <Button
                  variant=\"outline\"
                  size=\"sm\"
                  className=\"flex-1\"
                  onClick={handleUndo}
                  disabled={customizations.length === 0}
                >
                  <RotateCcw className=\"w-4 h-4 mr-2\" />
                  실행 취소
                </Button>
              </div>
              
              <Button
                variant=\"ghost\"
                size=\"sm\"
                className=\"w-full text-red-600 hover:text-red-700 hover:bg-red-50\"
                onClick={handleReset}
                disabled={!hasChanges}
              >
                모든 변경사항 초기화
              </Button>
            </div>

            {/* Customization Summary */}
            {customizations.length > 0 && (
              <div className=\"mt-4 p-3 bg-blue-50 rounded-lg\">
                <div className=\"flex items-center gap-2 mb-2\">
                  <Zap className=\"w-4 h-4 text-blue-600\" />
                  <span className=\"text-sm font-medium text-blue-900\">
                    변경사항 {customizations.length}개
                  </span>
                </div>
                <div className=\"text-xs text-blue-700\">
                  {session && `세션: ${session.session_id.slice(0, 8)}...`}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Customization Panel */}
      <div className=\"flex-1 flex flex-col\">
        {/* Header */}
        <div className=\"flex-none p-4 border-b border-gray-200\">
          <div className=\"flex items-center justify-between\">
            <div>
              <h2 className=\"text-xl font-semibold text-gray-900\">템플릿 커스터마이징</h2>
              <p className=\"text-sm text-gray-600 mt-1\">{template.name}</p>
            </div>
            
            {onClose && (
              <Button variant=\"ghost\" size=\"sm\" onClick={onClose}>
                <X className=\"w-4 h-4\" />
              </Button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className=\"flex-none border-b border-gray-200\">
          <div className=\"flex\">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 border-b-2 transition-colors',
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 bg-blue-50'
                    : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                )}
              >
                {tab.icon}
                <span className=\"text-sm font-medium\">{tab.label}</span>
                {tab.badge && tab.badge > 0 && (
                  <Badge variant=\"primary\" size=\"sm\">
                    {tab.badge}
                  </Badge>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className=\"flex-1 overflow-y-auto p-6\">
          <AnimatePresence mode=\"wait\">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === 'colors' && renderColorCustomization()}
              {activeTab === 'text' && renderTextCustomization()}
              {activeTab === 'images' && renderImageCustomization()}
              {activeTab === 'layout' && renderLayoutCustomization()}
              {activeTab === 'effects' && renderEffectsCustomization()}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Save Preset Modal */}
      <Modal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        title=\"프리셋 저장\"
        size=\"md\"
      >
        <div className=\"space-y-4\">
          <div>
            <label className=\"block text-sm font-medium text-gray-700 mb-1\">
              프리셋 이름 *
            </label>
            <input
              type=\"text\"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              placeholder=\"예: 봄 테마 색상\"
              className=\"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent\"
            />
          </div>
          
          <div>
            <label className=\"block text-sm font-medium text-gray-700 mb-1\">
              설명 (선택사항)
            </label>
            <textarea
              value={presetDescription}
              onChange={(e) => setPresetDescription(e.target.value)}
              placeholder=\"프리셋에 대한 간단한 설명을 입력하세요...\"
              rows={3}
              className=\"w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none\"
            />
          </div>

          <div className=\"flex gap-3 pt-4\">
            <Button
              variant=\"outline\"
              className=\"flex-1\"
              onClick={() => setShowSaveModal(false)}
            >
              취소
            </Button>
            <Button
              variant=\"primary\"
              className=\"flex-1\"
              onClick={handleSavePreset}
              disabled={!presetName.trim()}
            >
              <Save className=\"w-4 h-4 mr-2\" />
              저장
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default TemplateCustomizer;