/**
 * 간단한 마크다운 렌더러 - 스트리밍과 완료 상태 모두 동일하게 적용
 */

import React from 'react';

interface SimpleMarkdownProps {
  text: string;
  className?: string;
}

export const SimpleMarkdown: React.FC<SimpleMarkdownProps> = ({ text, className = '' }) => {
  // 마크다운을 HTML로 변환
  const convertToHtml = (markdown: string): string => {
    let html = markdown;
    
    // HTML 이스케이프
    html = html
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    
    // 헤더 변환 (## 제목)
    html = html.replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mt-4 mb-2">$1</h2>');
    
    // 헤더 변환 (# 제목)  
    html = html.replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold text-slate-900 dark:text-slate-100 mt-4 mb-3">$1</h1>');
    
    // 굵은 글씨 (**텍스트**)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-slate-900 dark:text-slate-100">$1</strong>');
    
    // 리스트 아이템 (- 항목)
    html = html.replace(/^- (.+)$/gm, '<div class="flex items-start ml-4 mb-1"><span class="text-slate-600 dark:text-slate-400 mr-2">•</span><span>$1</span></div>');
    
    // 인라인 코드 (`코드`)
    html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-sm font-mono text-slate-800 dark:text-slate-200">$1</code>');
    
    // 줄바꿈 처리
    html = html.replace(/\n/g, '<br>');
    
    return html;
  };

  const htmlContent = convertToHtml(text);

  return (
    <div 
      className={`markdown-content ${className}`}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
};