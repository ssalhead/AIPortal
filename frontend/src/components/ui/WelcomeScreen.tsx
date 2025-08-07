/**
 * 환영 화면 컴포넌트 - Gemini 스타일
 */

import React from 'react';
import { Bot, Globe, BookOpen, Palette, FileText } from 'lucide-react';
import type { AgentType } from '../../types';

interface FeatureCardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  colorClass: string;
  onClick: () => void;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ 
  icon: Icon, 
  title, 
  description, 
  colorClass, 
  onClick 
}) => (
  <button 
    onClick={onClick}
    className="w-full text-left bg-white dark:bg-slate-800/50 p-6 rounded-2xl border border-slate-200 dark:border-slate-700/50 
      hover:shadow-lg hover:-translate-y-1 transition-all duration-300 group"
  >
    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorClass} group-hover:scale-110 transition-transform duration-300`}>
      <Icon className="w-6 h-6 text-white" />
    </div>
    <h3 className="mt-4 text-lg font-semibold text-slate-800 dark:text-slate-200">
      {title}
    </h3>
    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
      {description}
    </p>
  </button>
);

interface WelcomeScreenProps {
  onFeatureSelect: (agentType: AgentType) => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onFeatureSelect }) => {
  const features = [
    {
      icon: Globe,
      title: '웹 검색',
      description: '실시간 최신 정보를 검색하여 정확하고 신뢰할 수 있는 답변을 제공합니다.',
      colorClass: 'bg-gradient-to-br from-green-500 to-green-600',
      agentType: 'web_search' as AgentType,
    },
    {
      icon: BookOpen,
      title: '심층 리서치',
      description: '특정 주제에 대해 다각도로 분석하고 종합적인 인사이트를 제공합니다.',
      colorClass: 'bg-gradient-to-br from-blue-500 to-blue-600',
      agentType: 'deep_research' as AgentType,
    },
    {
      icon: Palette,
      title: '창작 모드',
      description: '아이디어를 시각적으로 구체화하고 창의적인 콘텐츠를 생성합니다.',
      colorClass: 'bg-gradient-to-br from-purple-500 to-purple-600',
      agentType: 'none' as AgentType, // 창작은 기본 모드로 처리
    },
    {
      icon: Palette,
      title: 'Canvas',
      description: '인터랙티브 워크스페이스에서 아이디어를 시각화하고 협업합니다.',
      colorClass: 'bg-gradient-to-br from-orange-500 to-orange-600',
      agentType: 'canvas' as AgentType,
    },
  ];

  return (
    <div className="flex-grow flex items-center justify-center min-h-[60vh]">
      <div className="text-center max-w-4xl mx-auto px-4">
        {/* Hero Section */}
        <div className="mb-12">
          <div className="inline-flex w-20 h-20 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 items-center justify-center mb-6 shadow-lg">
            <Bot className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-slate-900 to-slate-600 text-transparent bg-clip-text dark:from-white dark:to-slate-400 mb-4">
            무엇을 도와드릴까요?
          </h2>
          <p className="text-xl text-slate-600 dark:text-slate-400 leading-relaxed max-w-2xl mx-auto">
            Claude, Gemini 등 다양한 AI 모델의 힘을 활용하여<br />
            아래 기능 중 하나를 선택하거나, 궁금한 점을 바로 질문해보세요.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
              colorClass={feature.colorClass}
              onClick={() => onFeatureSelect(feature.agentType)}
            />
          ))}
        </div>

        {/* Additional Info */}
        <div className="mt-12 flex items-center justify-center space-x-6 text-sm text-slate-500 dark:text-slate-400">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>8개 AI 모델 사용 가능</span>
          </div>
          <div className="w-px h-4 bg-slate-300 dark:bg-slate-600"></div>
          <span>실시간 웹 검색 지원</span>
          <div className="w-px h-4 bg-slate-300 dark:bg-slate-600"></div>
          <span>멀티모달 문서 분석</span>
        </div>
      </div>
    </div>
  );
};