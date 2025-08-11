/**
 * 텍스트 노트 편집기 컴포넌트
 */

import React, { useState, useRef, useEffect } from 'react';
import { 
  Bold, 
  Italic, 
  Underline,
  AlignLeft,
  AlignCenter,
  AlignRight,
  List,
  ListOrdered,
  Undo,
  Redo,
  Save,
  Copy,
  Download,
  Palette
} from 'lucide-react';
import type { CanvasItem } from '../../types/canvas';

// 기존 Canvas 시스템용 인터페이스
interface CanvasTextNoteEditorProps {
  item: CanvasItem;
  onUpdate: (updates: Partial<CanvasItem>) => void;
}

// 새로운 Workspace 시스템용 인터페이스
interface WorkspaceTextNoteEditorProps {
  content: string;
  onChange: (content: string) => void;
  readOnly?: boolean;
}

type TextNoteEditorProps = CanvasTextNoteEditorProps | WorkspaceTextNoteEditorProps;

export const TextNoteEditor: React.FC<TextNoteEditorProps> = (props) => {
  // 타입 가드 함수
  const isCanvasProps = (props: TextNoteEditorProps): props is CanvasTextNoteEditorProps => {
    return 'item' in props && 'onUpdate' in props;
  };
  
  // 프롭스에 따른 초기 값 설정
  const isCanvas = isCanvasProps(props);
  const initialContent = isCanvas ? props.item.content.content || '' : props.content || '';
  const initialTitle = isCanvas ? props.item.content.title || '' : '';
  const readOnly = isCanvas ? false : props.readOnly || false;
  
  const [title, setTitle] = useState(initialTitle);
  const [content, setContent] = useState(initialContent);
  const [isBold, setIsBold] = useState(isCanvas ? props.item.content.formatting?.bold || false : false);
  const [isItalic, setIsItalic] = useState(isCanvas ? props.item.content.formatting?.italic || false : false);
  const [textColor, setTextColor] = useState(isCanvas ? props.item.content.formatting?.color || '#000000' : '#000000');
  const [wordCount, setWordCount] = useState(0);
  const [charCount, setCharCount] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  useEffect(() => {
    // 글자 수 계산
    setCharCount(content.length);
    setWordCount(content.trim().split(/\s+/).filter(word => word.length > 0).length);
  }, [content]);
  
  useEffect(() => {
    // 자동 높이 조절
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [content]);
  
  const handleSave = () => {
    setIsSaving(true);
    
    if (isCanvas) {
      props.onUpdate({
        content: {
          title,
          content,
          formatting: {
            bold: isBold,
            italic: isItalic,
            color: textColor
          }
        }
      });
    } else {
      props.onChange(content);
    }
    
    setTimeout(() => setIsSaving(false), 500);
  };
  
  const handleExport = () => {
    const exportContent = `# ${title}\n\n${content}\n\n---\n작성일: ${new Date().toLocaleString()}`;
    const blob = new Blob([exportContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    // Toast 메시지 표시 (실제 구현시 Toast 컴포넌트 사용)
    alert('클립보드에 복사되었습니다!');
  };
  
  const insertText = (before: string, after: string = '') => {
    if (!textareaRef.current) return;
    
    const start = textareaRef.current.selectionStart;
    const end = textareaRef.current.selectionEnd;
    const selectedText = content.substring(start, end);
    const newContent = 
      content.substring(0, start) + 
      before + selectedText + after + 
      content.substring(end);
    
    setContent(newContent);
    
    // 커서 위치 조정
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const newPosition = start + before.length + selectedText.length;
        textareaRef.current.setSelectionRange(newPosition, newPosition);
      }
    }, 0);
  };
  
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg">
      {/* 툴바 */}
      <div className="border-b border-slate-200 dark:border-slate-700 p-4">
        <div className="flex items-center justify-between mb-3">
          {isCanvas ? (
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onBlur={handleSave}
              placeholder="노트 제목"
              disabled={readOnly}
              className="text-xl font-bold bg-transparent border-none outline-none text-slate-900 dark:text-slate-100 placeholder-slate-400 disabled:opacity-50"
            />
          ) : (
            <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
              텍스트 노트
            </div>
          )}
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="복사"
            >
              <Copy className="w-4 h-4" />
            </button>
            <button
              onClick={handleExport}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="내보내기"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              className={`
                px-3 py-2 rounded-lg flex items-center gap-2 transition-all
                ${isSaving 
                  ? 'bg-green-500 text-white' 
                  : 'bg-blue-500 text-white hover:bg-blue-600'
                }
              `}
            >
              <Save className="w-4 h-4" />
              <span className="text-sm font-medium">
                {isSaving ? '저장됨' : '저장'}
              </span>
            </button>
          </div>
        </div>
        
        {/* 서식 도구 */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              setIsBold(!isBold);
              insertText('**', '**');
            }}
            disabled={readOnly}
            className={`
              p-2 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              ${isBold 
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-slate-100' 
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
              }
            `}
            title="굵게"
          >
            <Bold className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setIsItalic(!isItalic);
              insertText('*', '*');
            }}
            disabled={readOnly}
            className={`
              p-2 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              ${isItalic 
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-slate-100' 
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
              }
            `}
            title="기울임"
          >
            <Italic className="w-4 h-4" />
          </button>
          <button
            onClick={() => insertText('~~', '~~')}
            disabled={readOnly}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="취소선"
          >
            <Underline className="w-4 h-4" />
          </button>
          
          <div className="w-px h-6 bg-slate-300 dark:bg-slate-600 mx-1" />
          
          <button
            onClick={() => insertText('# ')}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            title="제목 1"
          >
            <span className="text-xs font-bold">H1</span>
          </button>
          <button
            onClick={() => insertText('## ')}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            title="제목 2"
          >
            <span className="text-xs font-bold">H2</span>
          </button>
          <button
            onClick={() => insertText('### ')}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            title="제목 3"
          >
            <span className="text-xs font-bold">H3</span>
          </button>
          
          <div className="w-px h-6 bg-slate-300 dark:bg-slate-600 mx-1" />
          
          <button
            onClick={() => insertText('- ')}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            title="목록"
          >
            <List className="w-4 h-4" />
          </button>
          <button
            onClick={() => insertText('1. ')}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            title="번호 목록"
          >
            <ListOrdered className="w-4 h-4" />
          </button>
          
          <div className="w-px h-6 bg-slate-300 dark:bg-slate-600 mx-1" />
          
          <button
            onClick={() => insertText('> ')}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            title="인용"
          >
            <AlignLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => insertText('```\n', '\n```')}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            title="코드 블록"
          >
            <span className="text-xs font-mono">{'{ }'}</span>
          </button>
          
          <div className="ml-auto flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              <Palette className="w-4 h-4" />
              <input
                type="color"
                value={textColor}
                onChange={(e) => setTextColor(e.target.value)}
                className="w-8 h-8 border border-slate-300 dark:border-slate-600 rounded cursor-pointer"
              />
            </label>
          </div>
        </div>
      </div>
      
      {/* 편집 영역 */}
      <div className="p-6">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            if (!isCanvas) {
              props.onChange(e.target.value);
            }
          }}
          onBlur={handleSave}
          readOnly={readOnly}
          placeholder="여기에 내용을 입력하세요... (Markdown 문법을 지원합니다)"
          className="w-full min-h-[400px] bg-transparent border-none outline-none resize-none text-slate-800 dark:text-slate-200 placeholder-slate-400 disabled:opacity-50"
          style={{
            fontWeight: isBold ? 'bold' : 'normal',
            fontStyle: isItalic ? 'italic' : 'normal',
            color: textColor
          }}
        />
      </div>
      
      {/* 상태 바 */}
      <div className="border-t border-slate-200 dark:border-slate-700 px-6 py-3">
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-4">
            <span>{wordCount} 단어</span>
            <span>{charCount} 글자</span>
          </div>
          <div className="flex items-center gap-2">
            {isCanvas && (
              <span>마지막 저장: {new Date(props.item.updatedAt).toLocaleTimeString()}</span>
            )}
            {readOnly && (
              <span className="text-yellow-600">읽기 전용</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};