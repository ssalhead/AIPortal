/**
 * streaming-markdown 라이브러리를 이용한 실시간 마크다운 렌더러
 * ChatGPT 스타일의 타이핑 효과 지원
 */

import React, { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import * as smd from 'streaming-markdown';
import DOMPurify from 'dompurify';
import './StreamingMarkdown.css';

export interface StreamingMarkdownProps {
  /** 초기 마크다운 텍스트 */
  text?: string;
  /** 추가 CSS 클래스 */
  className?: string;
  /** 스트리밍 모드 여부 */
  isStreaming?: boolean;
  /** 스트리밍 완료 시 콜백 */
  onStreamingComplete?: () => void;
}

export interface StreamingMarkdownRef {
  /** 마크다운 텍스트 청크 추가 (스트리밍용) */
  appendChunk: (chunk: string) => void;
  /** 스트리밍 완료 (파서 리셋) */
  endStreaming: () => void;
  /** 전체 텍스트 설정 (비스트리밍용) */
  setText: (text: string) => void;
  /** 내용 초기화 */
  clear: () => void;
}

export const StreamingMarkdown = forwardRef<StreamingMarkdownRef, StreamingMarkdownProps>(
  ({ text = '', className = '', isStreaming = false, onStreamingComplete }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const parserRef = useRef<any>(null);
    const rendererRef = useRef<any>(null);
    const isInitializedRef = useRef(false);

    // 기본 렌더러 사용하고 직접 DOM 조작으로 간단하게 처리
    const createRenderer = (element: HTMLElement) => {
      console.log('🎬 렌더러 생성:', element);
      
      // streaming-markdown의 기본 렌더러 사용
      try {
        const defaultRenderer = smd.default_renderer(element);
        console.log('✅ 기본 렌더러 생성 완료:', defaultRenderer);
        return defaultRenderer;
      } catch (error) {
        console.error('❌ 기본 렌더러 생성 실패:', error);
        // 폴백: 매우 간단한 렌더러
        return {
          data: { element },
          add_token: (data: any) => data,
          end_token: (data: any) => data,
          add_text: (data: { element: HTMLElement }, text: string) => {
            if (text && data.element) {
              data.element.appendChild(document.createTextNode(text));
            }
            return data;
          },
          set_attr: (data: any) => data
        };
      }
    };

    // 토큰 타입을 HTML 태그명으로 변환
    const getTagName = (tokenType: string): string | null => {
      const tagMap: Record<string, string> = {
        'heading': 'h2', // 기본 헤딩
        'heading_1': 'h1',
        'heading_2': 'h2',
        'heading_3': 'h3',
        'heading_4': 'h4',
        'heading_5': 'h5',
        'heading_6': 'h6',
        'paragraph': 'p',
        'strong': 'strong',
        'emphasis': 'em',
        'code_inline': 'code',
        'code_block': 'pre',
        'link': 'a',
        'list_item': 'li',
        'list_ordered': 'ol',
        'list_unordered': 'ul',
        'blockquote': 'blockquote',
        'thematic_break': 'hr',
        'text': 'span'
      };
      
      return tagMap[tokenType] || null;
    };

    // 토큰 타입에 따른 CSS 클래스 적용
    const applyTokenClasses = (element: HTMLElement, token: any) => {
      const typeClasses: Record<string, string> = {
        'heading_1': 'streaming-h1',
        'heading_2': 'streaming-h2',  
        'heading_3': 'streaming-h3',
        'heading': 'streaming-h2', // 기본 헤딩
        'paragraph': 'streaming-p',
        'strong': 'streaming-strong',
        'emphasis': 'streaming-em',
        'code_inline': 'streaming-code-inline',
        'code_block': 'streaming-code-block',
        'link': 'streaming-link',
        'list_item': 'streaming-li',
        'list_ordered': 'streaming-ol',
        'list_unordered': 'streaming-ul',
        'blockquote': 'streaming-blockquote'
      };

      const cssClass = typeClasses[token.type];
      if (cssClass) {
        element.className = cssClass;
      }
    };

    // 초기화
    const initialize = () => {
      if (!containerRef.current || isInitializedRef.current) return;

      // 렌더러와 파서 생성
      rendererRef.current = createRenderer(containerRef.current);
      parserRef.current = smd.parser(rendererRef.current);
      isInitializedRef.current = true;

      // 초기 텍스트가 있으면 처리
      if (text && !isStreaming) {
        setText(text);
      }
    };

    // 하이브리드 방식: 스트리밍 중에는 단순 텍스트, 완료 후 마크다운 파싱
    const appendChunk = (chunk: string) => {
      console.log('🚀 하이브리드 청크 처리 - 전체 텍스트:', chunk.substring(0, 100) + '...');
      if (containerRef.current && chunk) {
        // 스트리밍 중에는 전체 텍스트를 표시 (chunk는 이미 누적된 전체 텍스트)
        containerRef.current.textContent = chunk;
        console.log('📝 스트리밍 중: 전체 텍스트 업데이트 (길이:', chunk.length, ')');
      }
    };

    // 스트리밍 완료 - 전체 텍스트를 마크다운으로 파싱
    const endStreaming = () => {
      console.log('🏁 스트리밍 완료 - 마크다운 파싱 시작');
      if (containerRef.current) {
        const fullText = containerRef.current.textContent || '';
        console.log('📄 완성된 전체 텍스트:', fullText.substring(0, 200) + '...');
        
        // 컨테이너 초기화
        containerRef.current.innerHTML = '';
        
        // 새로운 파서로 전체 텍스트 파싱
        try {
          const newRenderer = createRenderer(containerRef.current);
          const newParser = smd.parser(newRenderer);
          
          console.log('🔄 전체 텍스트 마크다운 파싱 중...');
          smd.parser_write(newParser, fullText);
          smd.parser_end(newParser);
          
          console.log('✅ 마크다운 파싱 완료');
          
          // 파싱 결과 확인
          setTimeout(() => {
            const finalHTML = containerRef.current?.innerHTML;
            console.log('🎯 최종 마크다운 HTML:', finalHTML?.substring(0, 300) + '...');
            
            const elements = containerRef.current?.children;
            if (elements) {
              console.log('🏗️ 최종 생성된 요소들:', Array.from(elements).map(el => ({
                tag: el.tagName,
                class: el.className,
                text: el.textContent?.substring(0, 30) + '...'
              })));
            }
          }, 0);
          
        } catch (error) {
          console.error('❌ 마크다운 파싱 실패:', error);
          // 폴백: 원본 텍스트 유지
          containerRef.current.textContent = fullText;
        }
        
        onStreamingComplete?.();
      }
    };

    // 전체 텍스트 설정 (비스트리밍용)
    const setText = (newText: string) => {
      if (containerRef.current && parserRef.current) {
        // 컨테이너 초기화
        containerRef.current.innerHTML = '';
        
        // 새로운 렌더러 생성 (DOM 초기화 후)
        rendererRef.current = createRenderer(containerRef.current);
        parserRef.current = smd.parser(rendererRef.current);
        
        // 텍스트 전체 처리
        smd.parser_write(parserRef.current, newText);
        smd.parser_end(parserRef.current);
      }
    };

    // 내용 초기화
    const clear = () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
      
      if (parserRef.current) {
        smd.parser_end(parserRef.current);
      }
      
      // 새로운 파서 생성
      if (containerRef.current) {
        rendererRef.current = createRenderer(containerRef.current);
        parserRef.current = smd.parser(rendererRef.current);
      }
    };

    // ref 인터페이스 노출
    useImperativeHandle(ref, () => ({
      appendChunk,
      endStreaming,
      setText,
      clear
    }));

    // 컴포넌트 마운트 시 초기화
    useEffect(() => {
      initialize();
    }, []);

    // text prop 변경 시 처리 (비스트리밍 모드)
    useEffect(() => {
      if (!isStreaming && text && isInitializedRef.current) {
        setText(text);
      }
    }, [text, isStreaming]);

    return (
      <div 
        ref={containerRef}
        className={`streaming-markdown ${className}`}
      />
    );
  }
);

StreamingMarkdown.displayName = 'StreamingMarkdown';