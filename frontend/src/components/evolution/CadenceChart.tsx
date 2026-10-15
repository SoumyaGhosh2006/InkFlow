/**
 * CadenceChart Component
 * Visualizes sentence length variance (burstiness) of natural human cadence
 * compared against the flat, monotonic robotic profile typical of AI slop.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 3:
 * Proves that InkFlow twin rewrites preserve the author's natural rhythm peaks and valleys
 * rather than flattening everything into uniform 15-word machine cadences.
 */

import React from 'react';
import { Activity, ShieldCheck, Zap } from 'lucide-react';

export const CadenceChart: React.FC = () => {
  // Sample cadence distribution across consecutive sentences in an authorial session
  const sentenceCadences = [
    { sentence: 'S1', author: 6, robotic: 15, text: 'We missed the target.' },
    { sentence: 'S2', author: 24, robotic: 16, text: 'The downstream third-party cloud provider had an unannounced breaking change on their authentication endpoints that caused persistent latency timeouts.' },
    { sentence: 'S3', author: 8, robotic: 15, text: 'Our fallback gate responded within milliseconds.' },
    { sentence: 'S4', author: 14, robotic: 15, text: 'Service was restored completely before customer traffic peaked on Monday morning.' },
    { sentence: 'S5', author: 5, robotic: 16, text: 'All systems are normal.' },
    { sentence: 'S6', author: 19, robotic: 15, text: 'We documented the exact timeline and preventative measures in the engineering postmortem for leadership review.' },
    { sentence: 'S7', author: 11, robotic: 15, text: 'Let me know if you need additional logs.' },
  ];

  const maxWords = 28;

  return (
    <div className="p-6 rounded-3xl bg-surface border border-surface-border shadow-subtle space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 text-accent-primary" />
            <h3 className="text-base font-semibold text-ink-primary font-serif">
              Sentence Length Variance (Burstiness)
            </h3>
          </div>
          <p className="text-xs text-ink-secondary">
            Natural human writing varies dynamically between short punches and detailed explanations.
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-md bg-stone-900 inline-block" />
            <span className="font-medium text-ink-primary">Your Twin Cadence</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-0.5 bg-red-400 border-t border-dashed border-red-500 inline-block" />
            <span className="text-stone-500">Generic AI Flatline (~15w)</span>
          </div>
        </div>
      </div>

      {/* Cadence Bar Chart Visualizer */}
      <div className="space-y-3 pt-2">
        <div className="h-48 flex items-end justify-between gap-3 px-2 pb-6 border-b border-surface-border relative">
          {/* Flatline overlay for generic AI */}
          <div
            className="absolute left-0 right-0 border-b-2 border-dashed border-red-400/80 z-10 flex items-center justify-end pr-2 pointer-events-none"
            style={{ bottom: `${(15 / maxWords) * 100}%` }}
          >
            <span className="text-[10px] font-mono text-red-500 bg-surface/90 px-1 rounded">
              Robot Flatline (15.2 words)
            </span>
          </div>

          {sentenceCadences.map((item, index) => {
            const heightPercent = Math.round((item.author / maxWords) * 100);
            return (
              <div
                key={index}
                className="flex-1 flex flex-col items-center h-full justify-end group relative"
              >
                {/* Floating tooltip */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-full mb-2 w-48 p-2 rounded-lg bg-stone-900 text-stone-100 text-[11px] shadow-panel pointer-events-none z-30">
                  <span className="font-bold text-amber-400 block mb-0.5">
                    Sentence {index + 1}: {item.author} words
                  </span>
                  <span className="italic text-stone-300">"{item.text}"</span>
                </div>

                {/* Cadence Bar */}
                <div
                  className="w-full max-w-[42px] rounded-t-xl bg-stone-900 group-hover:bg-accent-primary transition-all duration-300 relative"
                  style={{ height: `${heightPercent}%` }}
                >
                  <span className="absolute top-1 left-0 right-0 text-center text-[10px] font-mono text-stone-200">
                    {item.author}w
                  </span>
                </div>

                <span className="text-[11px] font-mono text-stone-500 mt-2">
                  {item.sentence}
                </span>
              </div>
            );
          })}
        </div>

        {/* Evaluation Summary Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3 rounded-2xl bg-canvas border border-surface-border">
            <span className="text-[10px] uppercase tracking-wider text-ink-secondary block">
              Cadence Variance
            </span>
            <span className="text-xl font-serif font-medium text-ink-primary mt-0.5 block">
              ±7.8 words
            </span>
            <span className="text-[11px] text-emerald-600 flex items-center space-x-1 mt-0.5">
              <Zap className="w-3 h-3" />
              <span>High authentic burstiness</span>
            </span>
          </div>

          <div className="p-3 rounded-2xl bg-canvas border border-surface-border">
            <span className="text-[10px] uppercase tracking-wider text-ink-secondary block">
              Punctuation Pause Habit
            </span>
            <span className="text-xl font-serif font-medium text-ink-primary mt-0.5 block">
              Em-Dash Focus
            </span>
            <span className="text-[11px] text-stone-500 mt-0.5 block">
              3 pauses per 100 words
            </span>
          </div>

          <div className="p-3 rounded-2xl bg-canvas border border-surface-border">
            <span className="text-[10px] uppercase tracking-wider text-ink-secondary block">
              Slop Immunity
            </span>
            <span className="text-xl font-serif font-medium text-ink-primary mt-0.5 block">
              98.2%
            </span>
            <span className="text-[11px] text-emerald-600 flex items-center space-x-1 mt-0.5">
              <ShieldCheck className="w-3 h-3" />
              <span>Zero synthetic filler</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
