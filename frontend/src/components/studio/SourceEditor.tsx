/**
 * SourceEditor Component
 * Left pane raw draft editor with real-time AI Slop detection and highlighting.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 2:
 * Scans input text in real-time for synthetic AI buzzwords (delve, tapestry, crucial, testament),
 * underlining them in subtle amber to visualize robotic phrasing before transformation.
 */

import React, { useMemo } from 'react';
import { AlertTriangle, Trash2, BookOpen } from 'lucide-react';
import { useStudioStore } from '../../store/useStudioStore';

// Common synthetic AI slop keywords & phrases
const SLOP_PATTERNS = [
  'delve into',
  'delve',
  'tapestry of',
  'tapestry',
  'a testament to',
  'testament',
  'crucial',
  'furthermore',
  'in conclusion',
  'it is important to note that',
  'it is worth noting that',
  'pivotal',
  'beacon of',
  'foster a sense of',
  'intertwined',
  'unwavering commitment',
  'harnessing the power of',
];

const SAMPLE_SLOP_DRAFT = `Furthermore, it is a testament to our dedication that we delve into the tapestry of solutions to optimize deliverables. In conclusion, this is crucial for our upcoming roadmap and fosters unwavering commitment across teams.`;

export const SourceEditor: React.FC = () => {
  const { inputDraft, setInputDraft, inputType } = useStudioStore();

  // Find occurrences of slop words in the current draft
  const detectedSlopWords = useMemo(() => {
    if (!inputDraft) return [];
    const lower = inputDraft.toLowerCase();
    const matches: string[] = [];
    for (const pattern of SLOP_PATTERNS) {
      if (lower.includes(pattern)) {
        matches.push(pattern);
      }
    }
    return matches;
  }, [inputDraft]);

  const handleInsertSample = () => {
    setInputDraft(SAMPLE_SLOP_DRAFT);
  };

  const handleClear = () => {
    setInputDraft('');
  };

  return (
    <div className="flex-1 flex flex-col bg-surface border-r border-surface-border">
      {/* Pane Header */}
      <div className="px-6 py-3 border-b border-surface-border flex items-center justify-between bg-canvas/40">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">
            {inputType === 'raw_draft' ? 'Source Draft' : 'Bullet Outline'}
          </span>
          {detectedSlopWords.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-amber-50 text-accent-hover border border-amber-200 text-[11px] font-medium flex items-center space-x-1">
              <AlertTriangle className="w-3 h-3 text-accent-primary" />
              <span>{detectedSlopWords.length} slop phrases found</span>
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleInsertSample}
            className="text-xs text-ink-secondary hover:text-accent-primary font-medium flex items-center space-x-1 transition-colors"
          >
            <BookOpen className="w-3 h-3" />
            <span>Load AI Slop Sample</span>
          </button>

          {inputDraft && (
            <button
              onClick={handleClear}
              className="text-xs text-stone-400 hover:text-red-500 transition-colors"
              title="Clear input"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Editor Body */}
      <div className="flex-1 p-6 relative flex flex-col">
        <textarea
          value={inputDraft}
          onChange={(e) => setInputDraft(e.target.value)}
          placeholder={
            inputType === 'raw_draft'
              ? 'Paste your draft here (e.g. unpolished email, report section, or AI draft). InkFlow will identify slop and rewrite it in your Style Genome...'
              : '- Point 1: API broke on Friday due to unexpected breaking changes\n- Point 2: We restored service by Saturday 2 PM\n- Point 3: Need to communicate this gently to the client'
          }
          className="w-full flex-1 bg-transparent text-base font-normal leading-relaxed text-ink-primary focus:outline-none resize-none placeholder:text-stone-400 font-sans"
        />

        {/* Slop Highlights: Compact on Mobile, Full Badges on Desktop */}
        {detectedSlopWords.length > 0 && (
          <>
            {/* Mobile Compact Alert Strip */}
            <div className="mt-2 pt-2 border-t border-stone-200/60 flex sm:hidden items-center justify-between text-xs text-amber-900 bg-amber-50/70 px-3 py-1.5 rounded-xl border border-amber-200/80 shrink-0">
              <span className="font-semibold">⚠️ {detectedSlopWords.length} AI slop phrases detected</span>
              <span className="text-[10px] text-stone-500 font-sans">Auto-purged on Humanize</span>
            </div>

            {/* Desktop Full Pattern Chips */}
            <div className="mt-4 pt-3 border-t border-stone-200/60 hidden sm:block">
              <span className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider block mb-1.5">
                Detected Synthetic Patterns:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {detectedSlopWords.map((word, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-300 text-amber-900 text-xs font-mono font-medium line-through decoration-amber-500 decoration-1"
                  >
                    "{word}"
                  </span>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
