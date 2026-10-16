/**
 * TopBar Component
 * Segmented input mode toggle, context selector pills, and 500-word limit counter.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 2 and docs/backend.md Section 4:
 * Input length is capped at 500 words per pass to guarantee sub-15s response latency.
 */

import React from 'react';
import { Sparkles, FileText, ListOrdered, AlertCircle, Loader2 } from 'lucide-react';
import { useStudioStore } from '../../store/useStudioStore';
import type { RewriteContext } from '../../types/api';

const CONTEXT_OPTIONS: { id: RewriteContext; label: string; offsetHint: string }[] = [
  { id: 'work_formal', label: 'Work Formal', offsetHint: '+1.5 Formality' },
  { id: 'academic', label: 'Academic', offsetHint: '+1.0 Formality' },
  { id: 'chat', label: 'Workplace Chat', offsetHint: '-1.0 Formality' },
];

export const TopBar: React.FC = () => {
  const {
    inputType,
    setInputType,
    context,
    setContext,
    inputDraft,
    isTransforming,
    triggerTransform,
  } = useStudioStore();

  const wordCount = inputDraft.trim().split(/\s+/).filter(Boolean).length;
  const isOverLimit = wordCount > 1000;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 sm:p-4 bg-surface border-b border-surface-border">
      {/* Left: Input Mode Segmented Control & Context Selector */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1 sm:pb-0 max-w-full">
        <div className="flex items-center p-1 bg-surface-subtle rounded-xl border border-stone-200/60 shrink-0">
          <button
            onClick={() => setInputType('raw_draft')}
            className={`flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
              inputType === 'raw_draft'
                ? 'bg-surface text-ink-primary shadow-xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span><span className="hidden sm:inline">Paste Existing </span>Draft</span>
          </button>

          <button
            onClick={() => setInputType('bullet_points')}
            className={`flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
              inputType === 'bullet_points'
                ? 'bg-surface text-ink-primary shadow-xs'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <ListOrdered className="w-3.5 h-3.5" />
            <span><span className="hidden sm:inline">Draft from </span>Bullets</span>
          </button>
        </div>

        {/* Context Selector Pills */}
        <div className="flex items-center space-x-1.5 pl-2 border-l border-stone-200 shrink-0">
          {CONTEXT_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => setContext(opt.id)}
              className={`px-2.5 sm:px-3 py-1.5 rounded-full text-xs font-medium transition-all shrink-0 ${
                context === opt.id
                  ? 'bg-amber-100 text-amber-900 border border-amber-300 font-semibold'
                  : 'bg-surface-subtle text-ink-secondary hover:text-ink-primary border border-transparent'
              }`}
              title={opt.offsetHint}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Right: Word Limit Meter & Transform CTA */}
      <div className="flex items-center justify-between sm:justify-end space-x-3 sm:space-x-4">
        {/* 1,000-Word Pass Limit Counter */}
        <div className="flex items-center space-x-1.5 text-xs font-mono">
          <span
            className={
              isOverLimit
                ? 'text-red-600 font-bold flex items-center space-x-1'
                : wordCount > 950
                ? 'text-amber-600 font-semibold'
                : 'text-ink-secondary'
            }
          >
            {isOverLimit && <AlertCircle className="w-3.5 h-3.5 mr-1" />}
            {wordCount} / 1,000 words
          </span>
          {isOverLimit && (
            <span className="text-[11px] text-red-500 font-sans">
              (Cap at 1,000w for quality passes)
            </span>
          )}
        </div>

        {/* Primary Action Button */}
        <button
          onClick={triggerTransform}
          disabled={isTransforming || wordCount === 0 || isOverLimit}
          className="px-5 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover disabled:bg-stone-300 disabled:cursor-not-allowed text-stone-900 font-semibold text-xs flex items-center space-x-2 shadow-xs transition-all cursor-pointer"
        >
          {isTransforming ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-stone-900" />
              <span>Humanizing...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-stone-900" />
              <span>Humanize Draft</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
