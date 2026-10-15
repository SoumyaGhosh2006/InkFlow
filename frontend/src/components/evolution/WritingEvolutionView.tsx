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

export const WritingEvolutionView: React.FC = () => {
  return (
    <div className="flex-1 overflow-y-auto p-8 bg-canvas">
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

        {/* Burstiness Bar Chart */}
        <CadenceChart />

        {/* Evolution & Shift Feed */}
        <EvolutionFeed />
      </div>
    </div>
  );
};
