import { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import clsx from 'clsx';

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmPhrase?: string; // If provided, requires user to type this phrase
  isDangerous?: boolean;
}

export function ConfirmModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmPhrase, 
  isDangerous = false 
}: ConfirmModalProps) {
  const [inputValue, setInputValue] = useState('');

  if (!isOpen) return null;

  const isConfirmDisabled = confirmPhrase 
    ? inputValue !== confirmPhrase 
    : false;

  const handleConfirm = () => {
    if (isConfirmDisabled) return;
    onConfirm();
    onClose();
    setInputValue(''); // Reset for next time
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md bg-[#1c1c1e] border border-white/10 rounded-2xl shadow-2xl transform transition-all scale-100">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className={clsx(
              "w-10 h-10 rounded-full flex items-center justify-center",
              isDangerous ? "bg-red-500/10 text-red-500" : "bg-blue-500/10 text-blue-500"
            )}>
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <p className="text-apple-gray leading-relaxed">
            {message}
          </p>

          {confirmPhrase && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-white/60 uppercase tracking-wider">
                Type <span className="text-white font-mono select-all">"{confirmPhrase}"</span> to confirm
              </label>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={`Type "${confirmPhrase}"`}
                className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-white placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 transition-all font-mono text-sm"
                autoFocus
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-white/5 bg-white/5 rounded-b-2xl">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isConfirmDisabled}
            className={clsx(
              "px-4 py-2 text-sm font-medium rounded-lg transition-all shadow-lg",
              isDangerous
                ? "bg-red-500 hover:bg-red-600 text-white shadow-red-500/20"
                : "bg-blue-500 hover:bg-blue-600 text-white shadow-blue-500/20",
              isConfirmDisabled && "opacity-50 cursor-not-allowed saturate-0"
            )}
          >
            {isDangerous ? 'Delete Everything' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}
