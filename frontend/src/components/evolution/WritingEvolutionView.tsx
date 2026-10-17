/**
 * WritingEvolutionView Component
 * Dedicated view hosting CadenceChart and EvolutionFeed.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 3:
 * Provides authorial transparency into burstiness, slop elimination,
 * and adaptive learning over time.
 */

import React from 'react';
import { CadenceChart } from './CadenceChart';
import { EvolutionFeed } from './EvolutionFeed';
import { useAuthStore } from '../../store/useAuthStore';

export const WritingEvolutionView: React.FC = () => {
  const { isAuthenticated, openAuthModal } = useAuthStore();
  const authed = isAuthenticated();

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 bg-canvas">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Page Title */}
        <div className="space-y-1">
          <h2 className="text-2xl font-serif font-medium text-ink-primary">
            Writing Evolution & Insights
          </h2>
          <p className="text-sm text-ink-secondary">
            Inspect your sentence cadence variance, synthetic slop elimination rate, and adaptive genome shifts.
          </p>
        </div>

        {!authed && (
          <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-300/80 text-amber-950 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
            <div>
              <p className="font-semibold text-sm">Personal Writing Evolution is Locked</p>
              <p className="text-amber-900/80 mt-0.5">
                Sign in to track your sentence cadence, burstiness, and train your personal Style Genome.
              </p>
            </div>
            <button
              onClick={() => openAuthModal('Sign in to view your writing evolution and train your model.')}
              className="px-3.5 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-stone-900 font-semibold shrink-0 cursor-pointer text-xs"
            >
              Sign In with Google
            </button>
          </div>
        )}

        {/* Burstiness Bar Chart */}
        <CadenceChart />

        {/* Evolution & Shift Feed */}
        <EvolutionFeed />
      </div>
    </div>
  );
};
