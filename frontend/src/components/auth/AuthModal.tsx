/**
 * AuthModal Component
 * Interactive modal prompting unauthenticated visitors to sign in with Google
 * whenever they attempt an action (humanizing, voice calibration, AI chat, learning).
 */

import React, { useEffect } from 'react';
import { X, Sparkles, Loader2, ShieldCheck, Zap } from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, authModalReason, closeAuthModal, loginWithGoogle, isLoading } =
    useAuthStore();

  useEffect(() => {
    if (!isAuthModalOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeAuthModal();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAuthModalOpen, closeAuthModal]);

  if (!isAuthModalOpen) return null;

  return (
    <div
      onClick={closeAuthModal}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/50 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-surface rounded-3xl border border-surface-border shadow-panel p-6 sm:p-8 space-y-6 animate-in zoom-in-95 duration-200 relative"
      >
        {/* Close Button */}
        <button
          onClick={closeAuthModal}
          aria-label="Close modal"
          className="absolute top-5 right-5 p-2 rounded-full text-stone-400 hover:text-ink-primary hover:bg-surface-subtle transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center space-y-2.5">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-amber-50 text-accent-primary flex items-center justify-center border border-amber-200/80 shadow-xs">
            <Sparkles className="w-6 h-6 text-accent-primary" />
          </div>

          <h2 className="text-xl sm:text-2xl font-serif font-medium text-ink-primary">
            Sign in to InkFlow
          </h2>

          <p className="text-xs sm:text-sm text-ink-secondary max-w-xs mx-auto leading-relaxed">
            {authModalReason || 'Sign in to access your personal Style Genome and calibrate your writing twin.'}
          </p>
        </div>

        {/* Value Highlights */}
        <div className="p-4 rounded-2xl bg-canvas border border-surface-border space-y-2.5 text-xs text-ink-primary">
          <div className="flex items-center space-x-2.5">
            <Zap className="w-4 h-4 text-accent-primary shrink-0" />
            <span><strong>5,000 daily words</strong> free quota resets daily</span>
          </div>
          <div className="flex items-center space-x-2.5">
            <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
            <span><strong>AI Slop Eradication</strong> & personalized Style Genome</span>
          </div>
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0" />
            <span><strong>Persistent session</strong> stays logged in automatically</span>
          </div>
        </div>

        {/* Action Button: Google Sign-in */}
        <div className="space-y-3">
          <button
            onClick={() => loginWithGoogle()}
            disabled={isLoading}
            className="w-full py-3 px-4 rounded-xl bg-surface hover:bg-stone-50 border border-stone-300 text-ink-primary font-semibold text-sm flex items-center justify-center space-x-3 shadow-xs hover:shadow-sm transition-all cursor-pointer disabled:opacity-60"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-stone-600" />
                <span>Signing you in...</span>
              </>
            ) : (
              <>
                {/* Official Google G Logo */}
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.35 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.16 0 9.97 0 12s.45 3.84 1.25 5.42l4.03-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
                <span>Continue with Google</span>
              </>
            )}
          </button>

          <p className="text-[11px] text-center text-ink-tertiary">
            By signing in, you agree to our Terms of Service & Privacy Policy.
          </p>
        </div>
      </div>
    </div>
  );
};
