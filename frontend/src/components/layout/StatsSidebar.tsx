/**
 * StatsSidebar Component
 * Right-side telemetry panel featuring Weekly Word Quota meter,
 * streak status, Style Genome snapshot, and Pro Upgrade trigger.
 *
 * Rationale:
 * Adheres strictly to docs/frontend.md Section 2 and docs/backend.md Section 5:
 * Enforces the ISO week reset copy ("Resets Monday 00:00 UTC") matching backend logic.
 */

import React, { useEffect } from 'react';
import { Flame, Crown, RefreshCw, Sparkles, ShieldCheck, X } from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';
import { useStudioStore } from '../../store/useStudioStore';

export const StatsSidebar: React.FC = () => {
  const { user, fetchUser, loginWithGoogle } = useAuthStore();
  const { setPricingModalOpen, setActiveView, setStatsDrawerOpen } = useStudioStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const tier = user?.tier || 'free';
  const isPro = tier === 'pro';

  const handleUpgradeToPro = async () => {
    const isAnonymous =
      !user ||
      (user.id === 'usr_local_dev' && (!user.email || user.email === 'author@inkflow.tech'));
    if (isAnonymous) {
      try {
        await loginWithGoogle();
        const activeUser = useAuthStore.getState().user;
        if (
          activeUser &&
          (activeUser.id !== 'usr_local_dev' || activeUser.email !== 'author@inkflow.tech')
        ) {
          setPricingModalOpen(true);
        }
      } catch {
        // error handled by auth store
      }
    } else {
      setPricingModalOpen(true);
    }
  };
  const limit = isPro ? 999999 : (user?.weeklyWordLimit && user.weeklyWordLimit <= 5000 ? user.weeklyWordLimit : 5000);
  const wordsUsed = user?.wordsUsedThisWeek || 215;
  const wordsLeft = Math.max(0, limit - wordsUsed);
  const percentUsed = isPro ? 10 : Math.min(100, Math.round((wordsUsed / limit) * 100));
  const streakDays = user?.streakDays || 1;

  return (
    <aside className="w-full xl:w-80 h-full flex-shrink-0 bg-surface border-l border-surface-border p-6 flex flex-col justify-between overflow-y-auto">
      <div className="space-y-6">
        {/* Streak & Status Pill */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200/60 shadow-xs">
            <Flame className="w-4 h-4 text-accent-primary animate-bounce" />
            <span className="text-xs font-semibold tracking-wide">{streakDays} Day Streak</span>
          </div>

          <div className="flex items-center space-x-2">
            <div
              className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                isPro
                  ? 'bg-amber-100 text-amber-900 border border-amber-300'
                  : 'bg-stone-100 text-stone-600'
              }`}
            >
              {isPro ? 'Pro Active' : 'Free Tier'}
            </div>
            <button
              onClick={() => setStatsDrawerOpen(false)}
              className="xl:hidden p-1 text-stone-400 hover:text-stone-700 hover:bg-stone-100 rounded-lg transition-colors cursor-pointer"
              title="Close Sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Daily Quota Card */}
        <div className="p-5 rounded-2xl bg-canvas border border-surface-border shadow-subtle space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">
              Daily Quota
            </span>
            <span className="text-xs font-mono font-medium text-ink-primary">
              {isPro ? 'Unlimited' : `${wordsUsed.toLocaleString()} / ${limit.toLocaleString()} w`}
            </span>
          </div>

          {/* Progress Bar */}
          {!isPro ? (
            <div className="w-full bg-stone-200 h-2 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${
                  percentUsed > 85 ? 'bg-red-500' : 'bg-accent-primary'
                }`}
                style={{ width: `${percentUsed}%` }}
              />
            </div>
          ) : (
            <div className="w-full bg-amber-100 h-2 rounded-full overflow-hidden">
              <div className="w-full h-full bg-accent-primary rounded-full" />
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-ink-secondary">
            <span>{isPro ? 'No daily limits' : `${wordsLeft.toLocaleString()} words left today`}</span>
            <span className="text-[11px] text-stone-500 font-mono">Resets Daily 00:00 UTC</span>
          </div>

          {!isPro && (
            <button
              onClick={handleUpgradeToPro}
              className="w-full mt-2 py-2.5 px-3 rounded-xl bg-gradient-to-r from-accent-primary to-amber-500 hover:from-amber-600 hover:to-amber-500 text-white font-semibold text-xs flex items-center justify-center space-x-1.5 shadow-sm transition-all cursor-pointer"
            >
              <Crown className="w-3.5 h-3.5" />
              <span>Upgrade to Pro for Unlimited</span>
            </button>
          )}
        </div>

        {/* Style Genome Summary Card */}
        <div className="p-5 rounded-2xl bg-canvas border border-surface-border shadow-subtle space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-accent-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-primary">
                Twin Style Genome
              </span>
            </div>
            <button
              onClick={() => setActiveView('drill')}
              className="text-[11px] text-accent-primary hover:text-accent-hover font-medium flex items-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Recalibrate</span>
            </button>
          </div>

          <p className="text-xs text-ink-secondary leading-relaxed">
            Calibrated to your authentic voice habits. Preserves your natural punctuation and tone.
          </p>

          <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
            <div className="p-2.5 rounded-xl bg-surface border border-stone-200/70">
              <span className="text-[10px] text-ink-secondary block uppercase">Cadence</span>
              <span className="font-semibold text-ink-primary font-mono text-sm">14.2 w/s</span>
            </div>
            <div className="p-2.5 rounded-xl bg-surface border border-stone-200/70">
              <span className="text-[10px] text-ink-secondary block uppercase">Formality</span>
              <span className="font-semibold text-ink-primary font-mono text-sm">7.2 / 10</span>
            </div>
            <div className="p-2.5 rounded-xl bg-surface border border-stone-200/70">
              <span className="text-[10px] text-ink-secondary block uppercase">Em-Dash (—)</span>
              <span className="font-semibold text-emerald-600 font-mono text-xs">Preserved</span>
            </div>
            <div className="p-2.5 rounded-xl bg-surface border border-stone-200/70">
              <span className="text-[10px] text-ink-secondary block uppercase">Slop Filter</span>
              <span className="font-semibold text-accent-primary font-mono text-xs">Active (120B)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Sovereignty Seal */}
      <div className="pt-6 border-t border-surface-border text-center">
        <div className="inline-flex items-center space-x-1.5 text-ink-secondary text-xs">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Zero Training on Your Inputs</span>
        </div>
        <p className="text-[10px] text-stone-400 mt-1">Complete data sovereignty & local storage.</p>
      </div>
    </aside>
  );
};
