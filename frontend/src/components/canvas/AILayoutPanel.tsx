/**
 * AI 레이아웃 패널 컴포넌트 v1.0
 * Canvas에 통합된 AI 레이아웃 도구 패널
 */

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Wand2,
  Grid,
  AlignCenter,
  Layout,
  Palette,
  Type,
  Target,
  TrendingUp,
  Settings,
  RefreshCw,
  CheckCircle,
  XCircle,
  Star,
  Lightbulb,
  Zap
} from 'lucide-react';
import { aiLayoutService } from '../../services/aiLayoutService';
import type {
  OptimizationSuggestion,
  SmartGrid,
  Template,
  AILayoutHint
} from '../../services/aiLayoutService';
import { useCanvasStore } from '../../stores/canvasStore';

interface AILayoutPanelProps {
  isOpen: boolean;
  onClose: () => void;
  canvasData?: any;
  onCanvasUpdate?: (newCanvasData: any) => void;
}

export const AILayoutPanel: React.FC<AILayoutPanelProps> = ({
  isOpen,
  onClose,
  canvasData,
  onCanvasUpdate
}) => {
  const [activeTab, setActiveTab] = useState<'suggestions' | 'templates' | 'grid' | 'hints'>('suggestions');
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [smartGrid, setSmartGrid] = useState<SmartGrid | null>(null);
  const [hints, setHints] = useState<AILayoutHint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisScore, setAnalysisScore] = useState<number>(0.5);

  // Canvas 상태
  const { items } = useCanvasStore();

  // AI 분석 및 제안 생성
  const generateSuggestions = useCallback(async () => {
    if (!canvasData) return;
    
    setIsLoading(true);
    try {
      const result = await aiLayoutService.getSuggestions(canvasData, {
        purpose: 'design',
        target_audience: 'general',
        brand_style: 'modern'
      });
      
      setSuggestions(result.suggestions);
      setAnalysisScore(result.performance_score);
    } catch (error) {
      console.error('AI 제안 생성 실패:', error);
    } finally {
      setIsLoading(false);
    }
  }, [canvasData]);

  // 스마트 그리드 생성
  const generateSmartGrid = useCallback(async (gridType: 'uniform' | 'golden_ratio' | 'rule_of_thirds' | 'dynamic' = 'dynamic') => {
    if (!canvasData?.stage) return;
    
    try {
      const grid = await aiLayoutService.generateSmartGrid(canvasData.stage, gridType);
      setSmartGrid(grid);
    } catch (error) {
      console.error('스마트 그리드 생성 실패:', error);
    }
  }, [canvasData]);

  // 템플릿 조회
  const loadTemplates = useCallback(async () => {
    setIsLoading(true);
    try {
      const templateList = await aiLayoutService.getTemplates({
        category: 'social_media' // 기본값, 추후 사용자 선택으로 변경
      });
      setTemplates(templateList);
    } catch (error) {
      console.error('템플릿 조회 실패:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 실시간 힌트 생성
  const generateHints = useCallback(async () => {
    if (!canvasData) return;
    
    try {
      const hintList = await aiLayoutService.getRealtimeHints(canvasData, {
        type: 'general_editing'
      });
      setHints(hintList);
    } catch (error) {
      console.error('실시간 힌트 생성 실패:', error);
    }
  }, [canvasData]);

  // 제안 적용
  const applySuggestion = async (suggestion: OptimizationSuggestion) => {
    try {
      if (suggestion.auto_fix_available) {
        await aiLayoutService.applyAutoFixes(canvasData, [suggestion.id]);
        await aiLayoutService.recordFeedback(suggestion.id, 'accepted');
        
        // 제안 목록에서 제거
        setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
        
        // Canvas 업데이트 (실제 구현에서는 백엔드에서 업데이트된 데이터를 받아옴)
        if (onCanvasUpdate) {
          // onCanvasUpdate(updatedCanvasData);
        }
      }
    } catch (error) {
      console.error('제안 적용 실패:', error);
    }
  };

  // 제안 거부
  const rejectSuggestion = async (suggestion: OptimizationSuggestion) => {
    try {
      await aiLayoutService.recordFeedback(suggestion.id, 'rejected');
      setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
    } catch (error) {
      console.error('제안 거부 실패:', error);
    }
  };

  // 템플릿 적용
  const applyTemplate = async (template: Template) => {
    try {
      const contentData = {
        title: '제목을 입력하세요',
        subtitle: '부제목을 입력하세요',
        description: '설명을 입력하세요'
      };
      
      const newCanvasData = await aiLayoutService.applyTemplate(
        template.template_id, 
        contentData,
        { color_palette: 'modern_blue' }
      );
      
      if (onCanvasUpdate) {
        onCanvasUpdate(newCanvasData);
      }
    } catch (error) {
      console.error('템플릿 적용 실패:', error);
    }
  };

  // 초기 로드
  useEffect(() => {
    if (isOpen && activeTab === 'suggestions') {
      generateSuggestions();
    } else if (isOpen && activeTab === 'templates') {
      loadTemplates();
    } else if (isOpen && activeTab === 'grid') {
      generateSmartGrid();
    } else if (isOpen && activeTab === 'hints') {
      generateHints();
    }
  }, [isOpen, activeTab, generateSuggestions, loadTemplates, generateSmartGrid, generateHints]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'critical': return <Zap className="w-4 h-4" />;
      case 'high': return <TrendingUp className="w-4 h-4" />;
      case 'medium': return <Target className="w-4 h-4" />;
      default: return <Lightbulb className="w-4 h-4" />;
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, x: 300 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 300 }}
          className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col"
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              <h2 className="text-lg font-semibold text-gray-900">AI 레이아웃</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
            >
              <XCircle className="w-5 h-5" />
            </button>
          </div>

          {/* 성능 점수 */}
          <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">레이아웃 점수</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${analysisScore * 100}%` }}
                  />
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {Math.round(analysisScore * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* 탭 네비게이션 */}
          <div className="flex border-b border-gray-200">
            {[
              { id: 'suggestions', label: '제안', icon: Wand2 },
              { id: 'templates', label: '템플릿', icon: Layout },
              { id: 'grid', label: '그리드', icon: Grid },
              { id: 'hints', label: '힌트', icon: Lightbulb }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex-1 flex items-center justify-center gap-1 py-3 text-xs font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* 콘텐츠 */}
          <div className="flex-1 overflow-y-auto">
            {/* 제안 탭 */}
            {activeTab === 'suggestions' && (
              <div className="p-4 space-y-4">
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw className="w-6 h-6 text-purple-600 animate-spin" />
                  </div>
                ) : suggestions.length > 0 ? (
                  suggestions.map((suggestion) => (
                    <motion.div
                      key={suggestion.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-gray-50 rounded-lg p-4 space-y-3"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          {getPriorityIcon(suggestion.priority)}
                          <h3 className="font-medium text-gray-900 text-sm">
                            {suggestion.title}
                          </h3>
                        </div>
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getPriorityColor(suggestion.priority)}`}>
                          {suggestion.priority}
                        </span>
                      </div>
                      
                      <p className="text-sm text-gray-600">
                        {suggestion.description}
                      </p>
                      
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Star className="w-3 h-3" />
                        <span>신뢰도: {Math.round(suggestion.confidence * 100)}%</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {suggestion.auto_fix_available && (
                          <button
                            onClick={() => applySuggestion(suggestion)}
                            className="flex-1 bg-purple-600 text-white text-xs py-2 px-3 rounded-md hover:bg-purple-700 transition-colors flex items-center justify-center gap-1"
                          >
                            <CheckCircle className="w-3 h-3" />
                            자동 수정
                          </button>
                        )}
                        <button
                          onClick={() => rejectSuggestion(suggestion)}
                          className="px-3 py-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
                        >
                          무시
                        </button>
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Sparkles className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm">AI 제안을 생성하려면 캔버스에 요소를 추가하세요</p>
                  </div>
                )}
              </div>
            )}

            {/* 템플릿 탭 */}
            {activeTab === 'templates' && (
              <div className="p-4 space-y-4">
                {templates.map((template) => (
                  <div
                    key={template.template_id}
                    className="bg-gray-50 rounded-lg p-4 cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => applyTemplate(template)}
                  >
                    <h3 className="font-medium text-gray-900 text-sm mb-2">
                      {template.name}
                    </h3>
                    <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                      <span className="bg-gray-200 px-2 py-1 rounded">{template.category}</span>
                      <span className="bg-gray-200 px-2 py-1 rounded">{template.style}</span>
                    </div>
                    <div className="text-xs text-gray-600">
                      {template.canvas_size.width} × {template.canvas_size.height}
                    </div>
                    {template.match_score && (
                      <div className="mt-2 flex items-center gap-2">
                        <Star className="w-3 h-3 text-yellow-500" />
                        <span className="text-xs text-gray-600">
                          매칭도: {Math.round(template.match_score * 20)}%
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* 그리드 탭 */}
            {activeTab === 'grid' && (
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'dynamic', label: '스마트', icon: Sparkles },
                    { id: 'golden_ratio', label: '황금비율', icon: Target },
                    { id: 'rule_of_thirds', label: '삼분할법', icon: Grid },
                    { id: 'uniform', label: '균등', icon: AlignCenter }
                  ].map((grid) => (
                    <button
                      key={grid.id}
                      onClick={() => generateSmartGrid(grid.id as any)}
                      className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors flex flex-col items-center gap-2 text-xs"
                    >
                      <grid.icon className="w-5 h-5 text-gray-600" />
                      {grid.label}
                    </button>
                  ))}
                </div>
                
                {smartGrid && (
                  <div className="bg-blue-50 rounded-lg p-4">
                    <h3 className="font-medium text-blue-900 text-sm mb-2">
                      {smartGrid.type} 그리드 생성됨
                    </h3>
                    <div className="text-xs text-blue-700">
                      <p>수직선: {smartGrid.vertical_lines.length}개</p>
                      <p>수평선: {smartGrid.horizontal_lines.length}개</p>
                      {smartGrid.focal_points && (
                        <p>주요 포인트: {smartGrid.focal_points.length}개</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 힌트 탭 */}
            {activeTab === 'hints' && (
              <div className="p-4 space-y-4">
                {hints.map((hint, index) => (
                  <div key={index} className="bg-yellow-50 rounded-lg p-4 border-l-4 border-yellow-400">
                    <h3 className="font-medium text-yellow-900 text-sm mb-1">
                      {hint.title}
                    </h3>
                    <p className="text-sm text-yellow-800">
                      {hint.description}
                    </p>
                    {hint.suggested_colors && (
                      <div className="mt-2 flex gap-2">
                        {hint.suggested_colors.map((color, i) => (
                          <div
                            key={i}
                            className="w-6 h-6 rounded border-2 border-white shadow-sm"
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                
                {hints.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <Lightbulb className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm">작업 중에 실시간 힌트를 제공합니다</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 하단 액션 */}
          <div className="p-4 border-t border-gray-200">
            <button
              onClick={generateSuggestions}
              disabled={isLoading}
              className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              AI 분석 새로고침
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AILayoutPanel;