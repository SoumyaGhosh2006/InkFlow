/**
 * AppHeader Component
 * Top application bar adhering to the Wispr Flow aesthetic.
 *
 * Rationale:
 * Features minimal warm porcelain styling, subtle breadcrumb markers,
 * and quick access to Pro status or profile identity.
 */

import React from 'react';
import { Crown, Sparkles, CheckCircle2, LogIn, LogOut, Flame } from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';
import { useStudioStore } from '../../store/useStudioStore';

export const AppHeader: React.FC = () => {
  const { user, loginWithGoogle, logout, isLoading } = useAuthStore();
  const { activeView, setActiveView, setPricingModalOpen, setStatsDrawerOpen } = useStudioStore();

  const getTitle = () => {
    switch (activeView) {
      case 'studio':
        return 'Humanize Studio';
      case 'chat':
        return 'AI Chat Writer';
      case 'drill':
        return 'Voice Calibration Drill (2-Min)';
      case 'evolution':
        return 'Writing Evolution & Evals';
      case 'pricing':
        return 'Subscription Plans';
      default:
        return 'Humanize';
    }
  };

  const isPro = user?.tier === 'pro';
  const isAnonymous =
    !user ||
    (user.id === 'usr_local_dev' && (!user.email || user.email === 'author@inkflow.tech'));

  const handleGetPro = async () => {
    if (isAnonymous) {
      try {
        await loginWithGoogle();
        const activeUser = useAuthStore.getState().user;
        if (activeUser && (activeUser.id !== 'usr_local_dev' || activeUser.email !== 'author@inkflow.tech')) {
          setPricingModalOpen(true);
        }
      } catch {
        // Handled in auth store
      }
    } else {
      setPricingModalOpen(true);
    }
  };

  return (
    <header className="h-16 flex-shrink-0 bg-surface border-b border-surface-border px-4 sm:px-6 md:px-8 flex items-center justify-between select-none z-10">
      {/* Brand & Breadcrumb */}
      <div className="flex items-center space-x-3 sm:space-x-4 min-w-0">
        <div className="flex items-center space-x-2 flex-shrink-0">
          <span className="text-lg sm:text-xl font-bold tracking-tight text-ink-primary font-serif">
            InkFlow
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
        </div>

        <span className="text-stone-300 font-light">/</span>

        <h1 className="text-xs sm:text-sm font-medium text-ink-secondary truncate">
          {getTitle()}
        </h1>
      </div>

      {/* Right Controls & User Info */}
      <div className="flex items-center space-x-2 sm:space-x-4 flex-shrink-0">
        {/* Mobile Stats / Quota Toggle Button */}
        <button
          onClick={() => setStatsDrawerOpen(true)}
          className="flex xl:hidden items-center space-x-1.5 px-2.5 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200/80 text-xs font-semibold shadow-2xs transition-all cursor-pointer"
          title="Open Daily Quota & Biometric Genome"
        >
          <Flame className="w-3.5 h-3.5 text-accent-primary" />
          <span className="hidden sm:inline">Daily Quota</span>
        </button>

        {/* Backend Status indicator (desktop only) */}
        <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-surface-subtle border border-surface-border text-xs text-ink-secondary">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>API Connected (Groq 120B)</span>
        </div>

        {!isPro ? (
          <button
            onClick={handleGetPro}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300/80 text-xs font-semibold shadow-xs transition-all cursor-pointer"
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

        {/* User Auth: Google Sign-in or Avatar */}
        {isAnonymous ? (
          <button
            onClick={() => loginWithGoogle()}
            disabled={isLoading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-surface hover:bg-stone-100 text-ink-primary border border-surface-border text-xs font-semibold shadow-xs transition-all"
          >
            <LogIn className="w-3.5 h-3.5 text-stone-600" />
            <span>Sign In</span>
          </button>
        ) : (
          <div className="flex items-center space-x-2 pl-2 border-l border-surface-border">
            <button
              onClick={() => setActiveView('evolution')}
              title={`View ${user.displayName || 'Author'}'s Personal Writing Dashboard (⌘3)`}
              className="flex items-center space-x-2 p-1 rounded-xl hover:bg-surface-subtle transition-colors group cursor-pointer text-left"
            >
              {user.photoUrl ? (
                <img
                  src={user.photoUrl}
                  alt={user.displayName || 'Author'}
                  className="w-8 h-8 rounded-full border border-surface-border object-cover"
                />
              ) : (
                <div
                  className="w-8 h-8 rounded-full bg-gradient-to-tr from-amber-600 to-amber-500 text-stone-100 flex items-center justify-center text-xs font-bold font-serif shadow-xs"
                >
                  {user.displayName ? user.displayName.slice(0, 1).toUpperCase() : 'A'}
                </div>
              )}
              <div className="hidden lg:flex flex-col">
                <span className="text-xs font-semibold text-ink-primary group-hover:text-accent-primary transition-colors truncate max-w-[120px]">
                  {user.displayName || 'Author'}
                </span>
                <span className="text-[10px] text-ink-tertiary uppercase tracking-wider">
                  {user.tier}
                </span>
              </div>
            </button>
            <button
              onClick={() => logout()}
              title="Sign Out"
              className="p-1.5 hover:bg-stone-100 rounded-lg text-stone-400 hover:text-stone-700 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

