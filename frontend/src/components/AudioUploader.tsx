import React, { useState, useCallback } from 'react';
import { Upload, Loader2, FileAudio } from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

interface AudioUploaderProps {
  onUpload: (file: File) => void;
  isProcessing: boolean;
}

export function AudioUploader({ onUpload, isProcessing }: AudioUploaderProps) {
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('audio/') || file.type === 'video/mp4') {
        onUpload(file);
      } else {
        alert("Please upload an audio file or MP4 video.");
      }
    }
  }, [onUpload]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  }, [onUpload]);

  return (
    <div
      className={twMerge(
        "relative w-full h-72 rounded-2xl border border-dashed transition-all duration-300 flex flex-col items-center justify-center text-center p-8 cursor-pointer overflow-hidden group",
        dragActive 
          ? "border-apple-blue bg-apple-blue/10 scale-[1.02] shadow-xl shadow-apple-blue/10" 
          : "border-white/20 bg-white/5 hover:border-white/40 hover:bg-white/10",
        isProcessing && "cursor-not-allowed opacity-80"
      )}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={!isProcessing ? handleDrop : undefined}
    >
      <input
        type="file"
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed z-20"
        onChange={handleChange}
        accept="audio/*,video/mp4"
        disabled={isProcessing}
      />

      {/* Background Decor */}
      <div className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-apple-blue/10 blur-[80px] rounded-full" />
      </div>

      {isProcessing ? (
        <div className="relative z-10 flex flex-col items-center gap-6 animate-in fade-in zoom-in duration-300">
          <div className="relative">
             <div className="absolute inset-0 bg-apple-blue/20 blur-xl rounded-full animate-pulse" />
             <Loader2 className="w-14 h-14 text-apple-blue animate-spin relative z-10" />
          </div>
          <div className="space-y-2">
            <h3 className="text-xl font-medium text-white">Analyzing Case</h3>
            <p className="text-sm text-apple-gray max-w-xs mx-auto leading-relaxed">
              Processing multimodal audio stream with Ali's powerful AI models
            </p>
          </div>
        </div>
      ) : (
        <div className="relative z-10 flex flex-col items-center gap-6 pointer-events-none">
          <div className={clsx(
              "w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300 shadow-lg",
              dragActive 
                ? "bg-apple-blue text-white shadow-apple-blue/30 scale-110" 
                : "bg-gradient-to-br from-white/10 to-white/5 border border-white/10 text-white/60 group-hover:text-white group-hover:scale-110"
          )}>
            {dragActive ? <FileAudio className="w-10 h-10" /> : <Upload className="w-10 h-10" />}
          </div>
          <div className="space-y-2">
            <h3 className="text-xl font-medium text-white group-hover:text-white transition-colors">
              {dragActive ? "Drop the audio file here" : "Upload Morning Report"}
            </h3>
            <p className="text-sm text-apple-gray group-hover:text-white/70 transition-colors">
              Drag and drop or click to browse <br />
              <span className="text-xs text-white/30 mt-1 block font-mono">(MP3, WAV, M4A, MP4)</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
