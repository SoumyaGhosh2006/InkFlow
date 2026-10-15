/**
 * AppHeader Component
 * Top application bar adhering to the Wispr Flow aesthetic.
 *
 * Rationale:
 * Features minimal warm porcelain styling, subtle breadcrumb markers,
 * and quick access to Pro status or profile identity.
 */

import React from 'react';
import { Crown, Sparkles, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';
import { useStudioStore } from '../../store/useStudioStore';

export const AppHeader: React.FC = () => {
  const { user } = useAuthStore();
  const { activeView, setPricingModalOpen } = useStudioStore();

  const getTitle = () => {
    switch (activeView) {
      case 'studio':
        return 'Transformation Studio';
      case 'drill':
        return '60-Second Voice Calibration Drill';
      case 'evolution':
        return 'Writing Evolution & Evals';
      case 'pricing':
        return 'Subscription Plans';
      default:
        return 'Studio';
    }
  };

  const isPro = user?.tier === 'pro';

  return (
    <header className="h-16 flex-shrink-0 bg-surface border-b border-surface-border px-8 flex items-center justify-between select-none z-10">
      {/* Brand & Breadcrumb */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <span className="text-xl font-bold tracking-tight text-ink-primary font-serif">
            InkFlow
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
        </div>

        <span className="text-stone-300 font-light">/</span>

        <h1 className="text-sm font-medium text-ink-secondary">
          {getTitle()}
        </h1>
      </div>

      {/* Right Controls & User Info */}
      <div className="flex items-center space-x-4">
        {/* Backend Status indicator */}
        <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-surface-subtle border border-surface-border text-xs text-ink-secondary">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>API Connected (Groq 120B)</span>
        </div>

        {!isPro ? (
          <button
            onClick={() => setPricingModalOpen(true)}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300/80 text-xs font-semibold shadow-xs transition-all"
          >
            <Crown className="w-3.5 h-3.5 text-accent-primary" />
            <span>Get Pro</span>
          </button>
        ) : (
          <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-stone-900 text-amber-400 text-xs font-semibold shadow-xs">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Pro Member</span>
          </span>
        )}

        {/* User Avatar */}
        <div className="flex items-center space-x-2 pl-2 border-l border-surface-border">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-stone-800 to-stone-600 text-stone-100 flex items-center justify-center text-xs font-bold font-serif">
            {user?.displayName ? user.displayName.slice(0, 1).toUpperCase() : 'A'}
          </div>
          <span className="hidden lg:inline text-xs font-medium text-ink-primary">
            {user?.displayName || 'Author'}
          </span>
        </div>
      </div>
    </header>
  );
};
