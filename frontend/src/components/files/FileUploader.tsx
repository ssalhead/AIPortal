/**
 * 파일 업로드 컴포넌트 - 드래그 앤 드롭 지원
 */

import React, { useState, useCallback, useRef } from 'react';
import { 
  Upload, 
  File as FileIcon, 
  Image, 
  FileText, 
  X, 
  CheckCircle,
  AlertCircle,
  Loader2,
  Plus
} from 'lucide-react';

interface UploadFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  progress: number;
  error?: string;
  result?: any;
}

interface FileUploaderProps {
  onUploadComplete?: (files: any[]) => void;
  onUploadStart?: () => void;
  onUploadProgress?: (progress: number) => void;
  maxFiles?: number;
  maxFileSize?: number; // bytes
  acceptedTypes?: string[];
  multiple?: boolean;
  disabled?: boolean;
  className?: string;
}

const SUPPORTED_TYPES = {
  'text/plain': { icon: FileText, color: 'text-gray-500', label: 'Text' },
  'application/pdf': { icon: FileIcon, color: 'text-red-500', label: 'PDF' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { icon: FileIcon, color: 'text-blue-500', label: 'Word' },
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { icon: FileIcon, color: 'text-green-500', label: 'Excel' },
  'text/csv': { icon: FileIcon, color: 'text-green-500', label: 'CSV' },
  'image/jpeg': { icon: Image, color: 'text-purple-500', label: 'Image' },
  'image/png': { icon: Image, color: 'text-purple-500', label: 'Image' },
  'image/gif': { icon: Image, color: 'text-purple-500', label: 'Image' },
  'image/webp': { icon: Image, color: 'text-purple-500', label: 'Image' },
  'application/json': { icon: FileText, color: 'text-yellow-500', label: 'JSON' },
  'text/markdown': { icon: FileText, color: 'text-blue-500', label: 'Markdown' },
  'application/x-python': { icon: FileText, color: 'text-green-600', label: 'Python' },
  'text/x-python': { icon: FileText, color: 'text-green-600', label: 'Python' },
  'application/javascript': { icon: FileText, color: 'text-yellow-600', label: 'JavaScript' },
  'application/typescript': { icon: FileText, color: 'text-blue-600', label: 'TypeScript' },
};

const DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const DEFAULT_MAX_FILES = 10;

export const FileUploader: React.FC<FileUploaderProps> = ({
  onUploadComplete,
  onUploadStart,
  onUploadProgress,
  maxFiles = DEFAULT_MAX_FILES,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  acceptedTypes,
  multiple = true,
  disabled = false,
  className = ""
}) => {
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const supportedTypes = acceptedTypes || Object.keys(SUPPORTED_TYPES);
  
  const getFileIcon = (mimeType: string) => {
    const typeInfo = SUPPORTED_TYPES[mimeType as keyof typeof SUPPORTED_TYPES];
    if (typeInfo) {
      const IconComponent = typeInfo.icon;
      return <IconComponent className={`w-5 h-5 ${typeInfo.color}`} />;
    }
    return <FileIcon className="w-5 h-5 text-gray-500" />;
  };
  
  const getFileTypeLabel = (mimeType: string) => {
    const typeInfo = SUPPORTED_TYPES[mimeType as keyof typeof SUPPORTED_TYPES];
    return typeInfo?.label || 'Unknown';
  };
  
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  const validateFile = (file: File): { valid: boolean; error?: string } => {
    // 파일 크기 검증
    if (file.size > maxFileSize) {
      return {
        valid: false,
        error: `파일 크기가 너무 큽니다. 최대 ${formatFileSize(maxFileSize)}까지 허용됩니다.`
      };
    }
    
    // MIME 타입 검증
    if (!supportedTypes.includes(file.type)) {
      return {
        valid: false,
        error: `지원하지 않는 파일 형식입니다. (${file.type})`
      };
    }
    
    return { valid: true };
  };
  
  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const filesToAdd: UploadFile[] = [];
    const files = Array.from(newFiles);
    
    // 파일 개수 제한 확인
    if (uploadFiles.length + files.length > maxFiles) {
      alert(`최대 ${maxFiles}개 파일까지 업로드 가능합니다.`);
      return;
    }
    
    files.forEach(file => {
      const validation = validateFile(file);
      
      if (validation.valid) {
        filesToAdd.push({
          id: Math.random().toString(36).substr(2, 9),
          file,
          status: 'pending',
          progress: 0
        });
      } else {
        alert(`${file.name}: ${validation.error}`);
      }
    });
    
    setUploadFiles(prev => [...prev, ...filesToAdd]);
  }, [uploadFiles.length, maxFiles, maxFileSize, supportedTypes]);
  
  const uploadFile = async (uploadFile: UploadFile) => {
    const formData = new FormData();
    formData.append('files', uploadFile.file);
    
    try {
      setUploadFiles(prev => prev.map(f => 
        f.id === uploadFile.id ? { ...f, status: 'uploading', progress: 0 } : f
      ));
      
      // 진행률 시뮬레이션 (실제 XMLHttpRequest 사용 시 onprogress 이벤트 활용)
      const progressInterval = setInterval(() => {
        setUploadFiles(prev => prev.map(f => {
          if (f.id === uploadFile.id && f.status === 'uploading') {
            const newProgress = Math.min(f.progress + Math.random() * 30, 90);
            return { ...f, progress: newProgress };
          }
          return f;
        }));
      }, 200);
      
      const response = await fetch('/api/v1/files/upload', {
        method: 'POST',
        body: formData,
      });
      
      clearInterval(progressInterval);
      
      if (response.ok) {
        const result = await response.json();
        setUploadFiles(prev => prev.map(f => 
          f.id === uploadFile.id 
            ? { ...f, status: 'completed', progress: 100, result: result[0] }
            : f
        ));
      } else {
        const error = await response.text();
        setUploadFiles(prev => prev.map(f => 
          f.id === uploadFile.id 
            ? { ...f, status: 'error', error: error || '업로드 실패' }
            : f
        ));
      }
    } catch (error) {
      setUploadFiles(prev => prev.map(f => 
        f.id === uploadFile.id 
          ? { ...f, status: 'error', error: String(error) }
          : f
      ));
    }
  };
  
  const uploadAllFiles = async () => {
    const pendingFiles = uploadFiles.filter(f => f.status === 'pending');
    
    if (pendingFiles.length === 0) return;
    
    onUploadStart?.();
    
    // 파일들을 순차적으로 업로드
    for (const file of pendingFiles) {
      await uploadFile(file);
    }
    
    // 업로드 완료 콜백
    const completedFiles = uploadFiles.filter(f => f.status === 'completed');
    if (completedFiles.length > 0) {
      onUploadComplete?.(completedFiles.map(f => f.result));
    }
  };
  
  const removeFile = (fileId: string) => {
    setUploadFiles(prev => prev.filter(f => f.id !== fileId));
  };
  
  const clearFiles = () => {
    setUploadFiles([]);
  };
  
  // 드래그 앤 드롭 핸들러
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);
  
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    if (disabled) return;
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      addFiles(files);
    }
  }, [addFiles, disabled]);
  
  // 파일 선택 핸들러
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      addFiles(files);
    }
    // 입력 값 리셋 (같은 파일 재선택 가능)
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  const openFileDialog = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };
  
  const pendingCount = uploadFiles.filter(f => f.status === 'pending').length;
  const uploadingCount = uploadFiles.filter(f => f.status === 'uploading').length;
  const completedCount = uploadFiles.filter(f => f.status === 'completed').length;
  const errorCount = uploadFiles.filter(f => f.status === 'error').length;
  
  return (
    <div className={`w-full ${className}`}>
      {/* 드래그 앤 드롭 영역 */}
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200
          ${isDragOver 
            ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20' 
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <div className="flex flex-col items-center space-y-4">
          <div className={`p-3 rounded-full ${isDragOver ? 'bg-blue-100 dark:bg-blue-800' : 'bg-gray-100 dark:bg-gray-700'}`}>
            <Upload className={`w-8 h-8 ${isDragOver ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} />
          </div>
          
          <div>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              파일을 여기에 드롭하거나 클릭하여 선택
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {multiple ? `최대 ${maxFiles}개` : '1개'} 파일, {formatFileSize(maxFileSize)} 이하
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
              지원 형식: PDF, Word, Excel, 이미지, 텍스트, 코드 파일
            </p>
          </div>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={supportedTypes.join(',')}
          onChange={handleFileSelect}
          className="hidden"
          disabled={disabled}
        />
      </div>
      
      {/* 파일 목록 */}
      {uploadFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
              선택된 파일 ({uploadFiles.length})
            </h4>
            
            <div className="flex items-center space-x-2">
              {pendingCount > 0 && (
                <button
                  onClick={uploadAllFiles}
                  disabled={disabled || uploadingCount > 0}
                  className="
                    px-3 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 
                    text-white text-xs rounded-md transition-colors
                    flex items-center space-x-1
                  "
                >
                  <Upload className="w-3 h-3" />
                  <span>업로드 ({pendingCount})</span>
                </button>
              )}
              
              <button
                onClick={clearFiles}
                disabled={disabled || uploadingCount > 0}
                className="
                  px-3 py-1.5 bg-gray-500 hover:bg-gray-600 disabled:bg-gray-400 
                  text-white text-xs rounded-md transition-colors
                "
              >
                모두 제거
              </button>
            </div>
          </div>
          
          {/* 업로드 상태 요약 */}
          {(uploadingCount > 0 || completedCount > 0 || errorCount > 0) && (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-4">
                  {uploadingCount > 0 && (
                    <span className="text-blue-600 dark:text-blue-400">
                      업로드 중: {uploadingCount}개
                    </span>
                  )}
                  {completedCount > 0 && (
                    <span className="text-green-600 dark:text-green-400">
                      완료: {completedCount}개
                    </span>
                  )}
                  {errorCount > 0 && (
                    <span className="text-red-600 dark:text-red-400">
                      실패: {errorCount}개
                    </span>
                  )}
                </div>
                
                <div className="text-gray-600 dark:text-gray-400">
                  총 {uploadFiles.length}개 파일
                </div>
              </div>
            </div>
          )}
          
          {/* 개별 파일 상태 */}
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {uploadFiles.map((uploadFile) => (
              <div
                key={uploadFile.id}
                className="
                  bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 
                  rounded-lg p-3 flex items-center space-x-3
                "
              >
                {/* 파일 아이콘 */}
                <div className="flex-shrink-0">
                  {getFileIcon(uploadFile.file.type)}
                </div>
                
                {/* 파일 정보 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {uploadFile.file.name}
                    </p>
                    
                    {/* 상태 아이콘 */}
                    <div className="flex-shrink-0 ml-2">
                      {uploadFile.status === 'pending' && (
                        <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600" />
                      )}
                      {uploadFile.status === 'uploading' && (
                        <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                      )}
                      {uploadFile.status === 'completed' && (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      )}
                      {uploadFile.status === 'error' && (
                        <AlertCircle className="w-5 h-5 text-red-500" />
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between mt-1">
                    <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>{formatFileSize(uploadFile.file.size)}</span>
                      <span>•</span>
                      <span>{getFileTypeLabel(uploadFile.file.type)}</span>
                    </div>
                    
                    {/* 제거 버튼 */}
                    {uploadFile.status !== 'uploading' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFile(uploadFile.id);
                        }}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  
                  {/* 진행률 바 */}
                  {uploadFile.status === 'uploading' && (
                    <div className="mt-2">
                      <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full">
                        <div 
                          className="h-1 bg-blue-500 rounded-full transition-all duration-300"
                          style={{ width: `${uploadFile.progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {Math.round(uploadFile.progress)}% 완료
                      </p>
                    </div>
                  )}
                  
                  {/* 에러 메시지 */}
                  {uploadFile.status === 'error' && uploadFile.error && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                      {uploadFile.error}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};