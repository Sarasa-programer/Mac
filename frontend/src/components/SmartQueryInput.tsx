import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Upload, FileText, Loader2, Brain, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import { 
  getGroqCompletions, 
  validateGroqQuery, 
  highlightGroqSyntax,
  type CompletionItem 
} from '../utils/groqSyntax';

interface SmartQueryInputProps {
  value: string;
  onChange: (value: string) => void;
  onExpand: () => void;
  suggestions?: string[];
  isExpanding?: boolean;
  placeholder?: string;
  className?: string;
}

export function SmartQueryInput({
  value,
  onChange,
  onExpand,
  suggestions = [],
  isExpanding = false,
  placeholder = "Describe clinical scenario ...",
  className
}: SmartQueryInputProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null);
  const [isAiContent, setIsAiContent] = useState(false);
  const [completions, setCompletions] = useState<CompletionItem[]>([]);
  const [showCompletions, setShowCompletions] = useState(false);
  const [activeCompletionIndex, setActiveCompletionIndex] = useState(0);
  const [validationError, setValidationError] = useState<string | null>(null);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-generate suggestion when empty
  useEffect(() => {
    if (!value && suggestions.length > 0) {
      const suggestion = suggestions[0];
      setAiSuggestion(suggestion);
    } else {
      setAiSuggestion(null);
    }
  }, [value, suggestions]);

  // Validation Effect
  useEffect(() => {
    if (value) {
      const error = validateGroqQuery(value);
      setValidationError(error);
    } else {
      setValidationError(null);
    }
  }, [value]);

  // Autocomplete Logic
  useEffect(() => {
    if (!value) {
      setCompletions([]);
      setShowCompletions(false);
      return;
    }
    
    const items = getGroqCompletions(value);
    setCompletions(items);
    setShowCompletions(items.length > 0);
    setActiveCompletionIndex(0);
  }, [value]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
        setIsDragging(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      processFile(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const processFile = async (file: File) => {
    setIsProcessingFile(true);
    try {
      let content = "";
      if (file.type === "text/plain" || file.name.endsWith(".txt")) {
        content = await file.text();
      } else {
        await new Promise(resolve => setTimeout(resolve, 1500));
        content = `Analysis of ${file.name}: Clinical features suggest Kawasaki Disease vs MIS-C`;
      }
      
      const query = content.slice(0, 100).replace(/\n/g, " ").trim();
      
      onChange(query);
      setIsAiContent(true);
    } catch (err) {
      console.error("File processing failed:", err);
    } finally {
      setIsProcessingFile(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showCompletions && completions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveCompletionIndex(prev => (prev + 1) % completions.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveCompletionIndex(prev => (prev - 1 + completions.length) % completions.length);
        return;
      }
      if (e.key === 'Tab' || e.key === 'Enter') {
        e.preventDefault();
        applyCompletion(completions[activeCompletionIndex]);
        return;
      }
      if (e.key === 'Escape') {
        setShowCompletions(false);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onExpand();
    }
  };

  const applyCompletion = (item: CompletionItem) => {
    const parts = value.split(/([\s\[\](){},]+)/);
    // Replace the last part (current word) with the completion
    // This is a simplified replacement logic
    const lastPart = parts[parts.length - 1];
    
    // Check if the last part matches start of completion
    if (lastPart && item.label.toLowerCase().startsWith(lastPart.toLowerCase())) {
        parts[parts.length - 1] = item.label;
    } else {
        parts.push(item.label);
    }
    
    const newValue = parts.join('');
    onChange(newValue);
    setShowCompletions(false);
    inputRef.current?.focus();
  };

  const applySuggestion = () => {
    if (aiSuggestion) {
      onChange(aiSuggestion);
      setIsAiContent(true);
      setAiSuggestion(null);
      inputRef.current?.focus();
    }
  };

  return (
    <div 
      ref={containerRef}
      className={clsx("relative group", className)}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag & Drop Overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-20 rounded-xl bg-blue-500/20 backdrop-blur-sm border-2 border-blue-500 border-dashed flex items-center justify-center animate-in fade-in duration-200 pointer-events-none">
          <div className="flex flex-col items-center gap-2 text-blue-200">
            <Upload className="w-8 h-8 animate-bounce" />
            <span className="font-medium">Drop file to analyze</span>
          </div>
        </div>
      )}

      {/* Processing Overlay */}
      {isProcessingFile && (
        <div className="absolute inset-0 z-20 rounded-xl bg-black/60 backdrop-blur-sm flex items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-white">
            <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
            <span className="text-sm font-medium">Processing file context...</span>
          </div>
        </div>
      )}

      {/* Autocomplete Dropdown */}
      {showCompletions && (
        <div className="absolute bottom-full left-0 mb-2 w-64 bg-[#1a1a1a] border border-white/10 rounded-lg shadow-xl overflow-hidden z-30 animate-in fade-in zoom-in-95 duration-100">
          <div className="text-[10px] text-white/40 px-3 py-1.5 border-b border-white/5 bg-white/5 uppercase tracking-wider font-medium">
            Ali suggestions
          </div>
          <div className="max-h-48 overflow-y-auto">
            {completions.map((item, index) => (
              <button
                key={`${item.label}-${index}`}
                onClick={() => applyCompletion(item)}
                className={clsx(
                  "w-full text-left px-3 py-2 text-sm font-mono flex items-center gap-2 transition-colors",
                  index === activeCompletionIndex ? "bg-blue-500/20 text-blue-300" : "text-white/70 hover:bg-white/5"
                )}
              >
                <span className={clsx(
                  "text-[10px] px-1.5 py-0.5 rounded border uppercase",
                  item.type === 'keyword' && "border-purple-500/30 text-purple-400 bg-purple-500/10",
                  item.type === 'function' && "border-yellow-500/30 text-yellow-400 bg-yellow-500/10",
                  item.type === 'operator' && "border-pink-500/30 text-pink-400 bg-pink-500/10",
                  item.type === 'field' && "border-blue-500/30 text-blue-400 bg-blue-500/10",
                )}>
                  {item.type.slice(0, 1).toUpperCase()}
                </span>
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="relative flex items-center">
        {/* Editor Container */}
        <div className="relative w-full">
            {/* Syntax Highlighter (Background) */}
            <div 
                className={clsx(
                    "absolute inset-0 w-full h-full px-4 py-3.5 pl-11 pr-32 font-mono text-sm pointer-events-none whitespace-pre-wrap break-words overflow-hidden",
                    // Match input styles exactly
                    "bg-transparent"
                )}
                aria-hidden="true"
            >
                {highlightGroqSyntax(value || (aiSuggestion ? "" : placeholder || ""))}
            </div>

            {/* Input Field (Transparent Foreground) */}
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => {
                onChange(e.target.value);
                setIsAiContent(false);
              }}
              onKeyDown={handleKeyDown}
              placeholder={aiSuggestion ? "" : placeholder}
              spellCheck={false}
              rows={1}
              className={clsx(
                "w-full bg-black/20 border rounded-xl px-4 py-3.5 pl-11 pr-32 transition-all duration-200 font-mono text-sm",
                "text-transparent caret-white placeholder-white/30 resize-none overflow-hidden", // Text transparent to show highlight
                "focus:outline-none focus:ring-2 focus:ring-blue-500/50",
                validationError ? "border-red-500/50 focus:ring-red-500/50" : (isAiContent ? "border-blue-500/30 bg-blue-500/5" : "border-white/10")
              )}
              style={{ minHeight: '48px' }} // Match height
              aria-label="ali Query Input"
            />
        </div>

        {/* Leading Icon */}
        <div className="absolute left-3.5 top-3.5 text-white/40 pointer-events-none z-10">
            {isAiContent ? (
                <Brain className="w-5 h-5 text-blue-400" />
            ) : (
                <Sparkles className="w-5 h-5" />
            )}
        </div>

        {/* AI Suggestion Ghost Text (Clickable) */}
        {!value && aiSuggestion && !isProcessingFile && (
            <div 
                onClick={applySuggestion}
                className="absolute left-11 top-0 bottom-0 flex items-center cursor-pointer group/suggestion z-10"
            >
                <span className="text-blue-300/60 italic group-hover/suggestion:text-blue-300 transition-colors">
                    Suggestion: {aiSuggestion}
                </span>
            </div>
        )}

        {/* Actions / Status */}
        <div className="absolute right-2 top-2 flex items-center gap-2 z-10">
            {/* File Upload Trigger */}
            {!value && (
                <label className="p-2 rounded-lg hover:bg-white/10 cursor-pointer text-white/40 hover:text-white transition-colors" title="Upload file context">
                    <input 
                        type="file" 
                        className="hidden" 
                        onChange={handleFileSelect}
                        accept=".txt,.pdf,.doc,.docx" 
                    />
                    <FileText className="w-4 h-4" />
                </label>
            )}

            {/* Expand Button */}
            <button
                onClick={onExpand}
                disabled={isExpanding || !value.trim() || !!validationError}
                className={clsx(
                    "px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2",
                    value.trim() && !validationError
                        ? "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 border border-blue-500/30" 
                        : "bg-white/5 text-white/20 cursor-not-allowed"
                )}
            >
                {isExpanding ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <>
                        Expand
                        <kbd className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-black/20 text-[10px] font-sans opacity-50">↵</kbd>
                    </>
                )}
            </button>
        </div>
      </div>
      
      {/* Status Indicators & Validation Error */}
      <div className="flex justify-between mt-2 px-1">
          <div className="flex flex-col gap-1">
            <div className="flex gap-2">
                {isAiContent && (
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/20 flex items-center gap-1">
                        <Brain className="w-3 h-3" />
                        AI Generated
                    </span>
                )}
                {value && !isAiContent && (
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-white/10 text-white/60 border border-white/10">
                        ALi`s Query
                    </span>
                )}
            </div>
            
            {/* Validation Error Message */}
            {validationError && (
                <span className="text-[10px] font-medium text-red-400 flex items-center gap-1.5 animate-in slide-in-from-top-1">
                    <AlertTriangle className="w-3 h-3" />
                    {validationError}
                </span>
            )}
          </div>
          
          <div className="text-[10px] text-white/30 self-start pt-0.5">
              research like Dr.Sara Ahadinia
          </div>
      </div>
    </div>
  );
}
