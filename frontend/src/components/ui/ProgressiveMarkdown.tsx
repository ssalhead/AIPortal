/**
 * 증분 기반 점진적 마크다운 렌더러
 * 실시간 스트리밍 중 새로 추가된 텍스트만 파싱하여 성능 최적화
 * ChatGPT 스타일의 자연스러운 실시간 마크다운 렌더링
 */

import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef, useCallback, useMemo } from 'react';
import { loggers } from '../../utils/logger';
import './StreamingMarkdown.css';

export interface ProgressiveMarkdownProps {
  /** 초기 마크다운 텍스트 */
  text?: string;
  /** 추가 CSS 클래스 */
  className?: string;
  /** 스트리밍 모드 여부 */
  isStreaming?: boolean;
  /** 스트리밍 완료 시 콜백 */
  onStreamingComplete?: () => void;
}

export interface ProgressiveMarkdownRef {
  /** 마크다운 텍스트 청크 추가 (스트리밍용) */
  appendChunk: (chunk: string) => void;
  /** 스트리밍 완료 */
  endStreaming: () => void;
  /** 전체 텍스트 설정 (비스트리밍용) */
  setText: (text: string) => void;
  /** 내용 초기화 */
  clear: () => void;
}

interface ParsedLine {
  id: string;
  element: React.ReactNode;
  raw: string;
  isComplete: boolean; // 줄이 완성되었는지 여부
  isGhost?: boolean; // Gemini 스타일 안개 효과 여부
}

interface IncrementalState {
  lastProcessedLength: number; // 마지막으로 처리된 텍스트 길이
  completedLines: ParsedLine[]; // 완성된 줄들 (캐시)
  currentLine: string; // 현재 진행 중인 줄
}

export const ProgressiveMarkdown = forwardRef<ProgressiveMarkdownRef, ProgressiveMarkdownProps>(
  ({ text = '', className = '', isStreaming = false, onStreamingComplete }, ref) => {
    const [incrementalState, setIncrementalState] = useState<IncrementalState>({
      lastProcessedLength: 0,
      completedLines: [],
      currentLine: ''
    });
    const [parsedLines, setParsedLines] = useState<ParsedLine[]>([]);
    const lineIdCounter = useRef(0);
    const fullTextRef = useRef<string>(''); // 전체 텍스트 참조 (성능 최적화)

    /**
     * 성능 모니터링 유틸리티
     */
    const performanceMonitor = useRef({
      parseStartTime: 0,
      totalParseTime: 0,
      parsedChunks: 0,
      averageParseTime: 0
    });

    /**
     * 마크다운 라인을 React 요소로 파싱
     */
    const parseMarkdownLine = useCallback((line: string, isLast: boolean = false): React.ReactNode => {
      // 빈 줄 처리
      if (line.trim() === '') {
        return <br />;
      }

      // 헤더 처리 (# ~ ######)
      const headerMatch = line.match(/^(#{1,6})\s+(.+)/);
      if (headerMatch) {
        const level = headerMatch[1].length;
        const content = parseInlineMarkdown(headerMatch[2]);
        switch (level) {
          case 1: return <h1>{content}</h1>;
          case 2: return <h2>{content}</h2>;
          case 3: return <h3>{content}</h3>;
          case 4: return <h4>{content}</h4>;
          case 5: return <h5>{content}</h5>;
          case 6: return <h6>{content}</h6>;
        }
      }

      // 리스트 아이템 처리
      const listMatch = line.match(/^[-*+]\s+(.+)/);
      if (listMatch) {
        return <li>{parseInlineMarkdown(listMatch[1])}</li>;
      }

      // 번호 리스트 처리
      const orderedListMatch = line.match(/^\d+\.\s+(.+)/);
      if (orderedListMatch) {
        return <li>{parseInlineMarkdown(orderedListMatch[1])}</li>;
      }

      // 인용문 처리
      const quoteMatch = line.match(/^>\s*(.+)/);
      if (quoteMatch) {
        return <blockquote>{parseInlineMarkdown(quoteMatch[1])}</blockquote>;
      }

      // 코드 블록 시작/종료
      if (line.startsWith('```')) {
        return <pre className="streaming-code-block">{line}</pre>;
      }

      // 구분선 처리
      if (line.match(/^[-*_]{3,}$/)) {
        return <hr />;
      }

      // 일반 문단 - 마지막 줄이고 불완전한 마크다운이 있을 수 있음
      if (isLast && isStreaming) {
        // 불완전한 마크다운은 그대로 표시
        return <p>{parseInlineMarkdownSafe(line)}</p>;
      }

      return <p>{parseInlineMarkdown(line)}</p>;
    }, [isStreaming]);

    /**
     * 인라인 마크다운 파싱 (굵은 글씨, 이탤릭, 코드 등) - 성능 최적화
     */
    const parseInlineMarkdown = useMemo(() => {
      // 메모이제이션을 위한 캐시
      const cache = new Map<string, React.ReactNode>();
      
      return (text: string): React.ReactNode => {
        // 캐시 확인
        const cached = cache.get(text);
        if (cached !== undefined) {
          return cached;
        }
        
        const elements: React.ReactNode[] = [];
        let lastIndex = 0;
        let keyCounter = 0;
        
        // 최적화된 단일 정규식으로 모든 패턴 매치
        const combinedRegex = /(\*\*([^*]+)\*\*)|(\*([^*]+)\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)]+)\))/g;
        let match;
        
        while ((match = combinedRegex.exec(text)) !== null) {
          // 매치 이전 텍스트 추가
          if (match.index > lastIndex) {
            elements.push(text.substring(lastIndex, match.index));
          }
          
          // 매치된 패턴에 따라 요소 생성
          if (match[1]) { // **bold**
            elements.push(<strong key={`bold-${keyCounter++}`}>{match[2]}</strong>);
          } else if (match[3]) { // *italic*
            elements.push(<em key={`italic-${keyCounter++}`}>{match[4]}</em>);
          } else if (match[5]) { // `code`
            elements.push(<code key={`code-${keyCounter++}`}>{match[6]}</code>);
          } else if (match[7]) { // [text](url)
            elements.push(<a key={`link-${keyCounter++}`} href={match[9]}>{match[8]}</a>);
          }
          
          lastIndex = match.index + match[0].length;
        }

        // 남은 텍스트 추가
        if (lastIndex < text.length) {
          elements.push(text.substring(lastIndex));
        }

        const result = elements.length > 0 ? <>{elements}</> : text;
        
        // 캐시에 저장 (최대 100개 항목만 유지)
        if (cache.size > 100) {
          const firstKey = cache.keys().next().value;
          cache.delete(firstKey);
        }
        cache.set(text, result);
        
        return result;
      };
    }, []);

    /**
     * 불완전한 마크다운도 안전하게 파싱
     */
    const parseInlineMarkdownSafe = useCallback((text: string): React.ReactNode => {
      // 닫히지 않은 마크다운 문법은 그대로 표시
      const openBold = (text.match(/\*\*/g) || []).length % 2 !== 0;
      const openItalic = (text.match(/\*/g) || []).length % 2 !== 0;
      const openCode = (text.match(/`/g) || []).length % 2 !== 0;
      
      if (openBold || openItalic || openCode) {
        // 불완전한 마크다운은 원본 그대로 표시
        return text;
      }
      
      return parseInlineMarkdown(text);
    }, [parseInlineMarkdown]);

    /**
     * 파싱된 줄 업데이트 (React 렌더링 최적화)
     */
    const updateParsedLines = useCallback((state: IncrementalState) => {
      const allLines: ParsedLine[] = [...state.completedLines];
      
      // 현재 진행 중인 줄 추가 (불완전할 수 있음) - Gemini 안개 효과
      if (state.currentLine) {
        const currentLineId = `current-line-${state.completedLines.length}`;
        allLines.push({
          id: currentLineId,
          element: parseMarkdownLine(state.currentLine, true),
          raw: state.currentLine,
          isComplete: false,
          isGhost: true // 진행 중인 줄은 안개 효과
        });
      }
      
      setParsedLines(allLines);
      // 성능 향상을 위해 디버깅 로그 제거
      // console.log('🎨 렌더링 업데이트 - 총 줄 수:', allLines.length, '완성된 줄:', state.completedLines.length);
    }, [parseMarkdownLine]);

    /**
     * 증분 청크 추가 - 새로 추가된 텍스트에서 줄바꿈 감지 및 실시간 파싱 (성능 최적화)
     */
    const appendChunk = useCallback((chunk: string) => {
      const startTime = performance.now();
      performanceMonitor.current.parseStartTime = startTime;
      
      // 성능 최적화를 위해 핵심 로그만 유지 (성능 디버깅 시에만 출력)
      loggers.perf('증분 파싱', {
        currentLength: chunk.length,
        newData: chunk.length - incrementalState.lastProcessedLength
      }, 'ProgressiveMarkdown');
      
      fullTextRef.current = chunk;
      
      // 새로 추가된 텍스트만 추출
      const newText = chunk.slice(incrementalState.lastProcessedLength);
      if (newText.length === 0) {
        return; // 새 텍스트가 없으면 조용히 종료
      }
      
      // 새 청크에서 줄바꿈 감지
      const hasLineBreak = newText.includes('\n');
      
      setIncrementalState(prevState => {
        const newCompletedLines = [...prevState.completedLines];
        let newCurrentLine = prevState.currentLine;
        
        if (hasLineBreak) {
          // 줄바꿈이 있는 경우 - 완성된 줄들과 새 진행 줄 분리
          const combinedText = prevState.currentLine + newText;
          const lines = combinedText.split('\n');
          
          // 마지막 줄을 제외한 모든 줄은 완성된 것으로 처리
          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i];
            const lineId = `line-${lineIdCounter.current++}`;
            
            const parsedLine: ParsedLine = {
              id: lineId,
              element: parseMarkdownLine(line, false),
              raw: line,
              isComplete: true,
              isGhost: false // 완성된 줄은 선명하게 (안개 → 선명 전환)
            };
            
            newCompletedLines.push(parsedLine);
          }
          
          // 마지막 줄은 새로운 진행 중인 줄
          newCurrentLine = lines[lines.length - 1] || '';
          
        } else {
          // 줄바꿈이 없는 경우 - 현재 줄에 텍스트만 추가
          newCurrentLine = prevState.currentLine + newText;
        }
        
        const newState = {
          lastProcessedLength: chunk.length,
          completedLines: newCompletedLines,
          currentLine: newCurrentLine
        };
        
        // 렌더링용 파싱된 줄 업데이트
        updateParsedLines(newState);
        
        // 성능 모니터링
        const endTime = performance.now();
        const parseTime = endTime - startTime;
        performanceMonitor.current.totalParseTime += parseTime;
        performanceMonitor.current.parsedChunks++;
        performanceMonitor.current.averageParseTime = 
          performanceMonitor.current.totalParseTime / performanceMonitor.current.parsedChunks;
        
        // 성능 로그는 필요시에만 활성화
        // console.log('⏱️ 파싱 성능:', Math.round(parseTime * 100) / 100 + 'ms');
        
        return newState;
      });
    }, [incrementalState.lastProcessedLength, incrementalState.currentLine, updateParsedLines, parseMarkdownLine]);
    
    /**
     * 스트리밍 완료 - 마지막 줄도 완성된 것으로 처리
     */
    const endStreaming = useCallback(() => {
      loggers.info('스트리밍 완료 - 최종 파싱', 'ProgressiveMarkdown');
      
      setIncrementalState(prevState => {
        const newCompletedLines = [...prevState.completedLines];
        
        // 현재 진행 중인 줄이 있으면 완성된 줄로 추가
        if (prevState.currentLine) {
          const finalLineId = `line-${lineIdCounter.current++}`;
          newCompletedLines.push({
            id: finalLineId,
            element: parseMarkdownLine(prevState.currentLine, false),
            raw: prevState.currentLine,
            isComplete: true,
            isGhost: false // 완성시 선명하게
          });
        }
        
        const finalState = {
          lastProcessedLength: prevState.lastProcessedLength,
          completedLines: newCompletedLines,
          currentLine: ''
        };
        
        updateParsedLines(finalState);
        onStreamingComplete?.();
        
        loggers.perf('최종 성능 통계', {
          totalParseTime: Math.round(performanceMonitor.current.totalParseTime) + 'ms',
          avgParseTime: Math.round(performanceMonitor.current.averageParseTime * 100) / 100 + 'ms',
          processedChunks: performanceMonitor.current.parsedChunks,
          finalLines: newCompletedLines.length
        }, 'ProgressiveMarkdown');
        
        return finalState;
      });
    }, [updateParsedLines, onStreamingComplete, parseMarkdownLine]);

    /**
     * 전체 텍스트 설정 (비스트리밍용)
     */
    const setText = useCallback((newText: string) => {
      fullTextRef.current = newText;
      const lines = newText.split('\n');
      
      const newCompletedLines: ParsedLine[] = lines.map((line, index) => ({
        id: `line-${index}`,
        element: parseMarkdownLine(line, false),
        raw: line,
        isComplete: true,
        isGhost: false // 비스트리밍 텍스트는 선명하게
      }));
      
      setIncrementalState({
        lastProcessedLength: newText.length,
        completedLines: newCompletedLines,
        currentLine: ''
      });
      
      setParsedLines(newCompletedLines);
    }, [parseMarkdownLine]);

    /**
     * 내용 초기화
     */
    const clear = useCallback(() => {
      fullTextRef.current = '';
      setIncrementalState({
        lastProcessedLength: 0,
        completedLines: [],
        currentLine: ''
      });
      setParsedLines([]);
      lineIdCounter.current = 0;
      
      // 성능 모니터 리셋
      performanceMonitor.current = {
        parseStartTime: 0,
        totalParseTime: 0,
        parsedChunks: 0,
        averageParseTime: 0
      };
    }, []);

    // ref 인터페이스 노출
    useImperativeHandle(ref, () => ({
      appendChunk,
      endStreaming,
      setText,
      clear,
    }));

    // 초기 텍스트 처리
    useEffect(() => {
      if (text && !isStreaming) {
        setText(text);
      }
    }, [text, isStreaming, setText]);

    // 렌더링된 줄들을 메모이제이션으로 최적화
    const renderedLines = useMemo(() => {
      return parsedLines.map(line => (
        <MemoizedLineRenderer key={line.id} line={line} />
      ));
    }, [parsedLines]);

    return (
      <div className={`streaming-markdown ${className} ${isStreaming ? 'streaming' : ''}`}>
        {renderedLines}
      </div>
    );
  }
);

/**
 * 개별 줄 렌더러 - React.memo로 불필요한 리렌더링 방지
 */
interface MemoizedLineRendererProps {
  line: ParsedLine;
}

const MemoizedLineRenderer = React.memo<MemoizedLineRendererProps>(({ line }) => {
  // Gemini 스타일 안개 효과 클래스 적용
  const lineClass = line.isGhost ? 'gemini-ghost-text' : 'gemini-completed-text';
  
  return (
    <div className={lineClass}>
      {line.element}
    </div>
  );
}, (prevProps, nextProps) => {
  // 줄의 내용이 동일하면 리렌더링 하지 않음
  return prevProps.line.id === nextProps.line.id && 
         prevProps.line.raw === nextProps.line.raw &&
         prevProps.line.isComplete === nextProps.line.isComplete &&
         prevProps.line.isGhost === nextProps.line.isGhost;
});

MemoizedLineRenderer.displayName = 'MemoizedLineRenderer';

ProgressiveMarkdown.displayName = 'ProgressiveMarkdown';