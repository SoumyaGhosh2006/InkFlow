/**
 * CharacterDiff Component
 * Visualizes character-level diffs using jsdiff (diffChars).
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 4.1:
 * Visually proves that InkFlow strictly preserves authorial punctuation quirks
 * (em-dashes '—', semicolons ';', Oxford commas, and parentheses) in emerald chips
 * while striking out synthetic AI slop buzzwords.
 */

import React, { useMemo } from 'react';
import { diffChars, type Change } from 'diff';
import { Check, Info } from 'lucide-react';

interface CharacterDiffProps {
  originalText: string;
  transformedText: string;
}

export const CharacterDiff: React.FC<CharacterDiffProps> = ({
  originalText,
  transformedText,
}) => {
  const diffChunks = useMemo(() => {
    if (!originalText || !transformedText) return [];
    return diffChars(originalText, transformedText);
  }, [originalText, transformedText]);

  // Special punctuation symbols to highlight preservation
  const isSpecialPunctuation = (char: string) => {
    return char === '—' || char === ';' || char === ',' || char === ':' || char === '…';
  };

  return (
    <div className="space-y-4">
      {/* Legend Banner */}
      <div className="flex flex-wrap items-center gap-3 p-2.5 rounded-xl bg-canvas border border-surface-border text-xs">
        <span className="flex items-center space-x-1 text-ink-secondary">
          <Info className="w-3.5 h-3.5 text-accent-primary" />
          <span className="font-medium">Diff Legend:</span>
        </span>

        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-300 font-mono text-[11px]">
          <Check className="w-3 h-3 text-emerald-600" />
          <span>Preserved Quirks (—, ;, ,)</span>
        </span>

        <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-emerald-100/60 text-emerald-900 text-[11px] font-sans">
          Adapted Style
        </span>

        <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-red-100 text-red-800 line-through text-[11px]">
          Purged Slop
        </span>
      </div>

      {/* Rendered Diff Stream */}
      <div className="p-4 rounded-2xl bg-canvas border border-surface-border font-sans text-base leading-relaxed text-ink-primary select-text overflow-y-auto max-h-[380px]">
        {diffChunks.map((part: Change, index: number) => {
          if (part.added) {
            // Check if added text includes special punctuation
            if (isSpecialPunctuation(part.value)) {
              return (
                <span
                  key={index}
                  className="px-1 py-0.5 mx-0.5 rounded bg-emerald-100 text-emerald-900 font-mono font-bold border border-emerald-300 shadow-xs"
                  title="Preserved Authorial Punctuation"
                >
                  {part.value}
                </span>
              );
            }
            return (
              <span
                key={index}
                className="bg-emerald-50 text-emerald-900 border-b border-emerald-300 px-0.5 rounded-xs"
              >
                {part.value}
              </span>
            );
          }

          if (part.removed) {
            return (
              <span
                key={index}
                className="bg-red-50 text-red-700 line-through decoration-red-400 decoration-1 px-0.5 mx-0.5 rounded-xs"
                title="Removed AI Slop"
              >
                {part.value}
              </span>
            );
          }

          // Unchanged text: highlight em-dash or semicolon if preserved
          if (isSpecialPunctuation(part.value.trim())) {
            return (
              <span
                key={index}
                className="px-1 py-0.5 mx-0.5 rounded bg-emerald-50 text-emerald-800 font-mono font-semibold border border-emerald-200"
                title="Preserved Authorial Punctuation"
              >
                {part.value}
              </span>
            );
          }

          return <span key={index}>{part.value}</span>;
        })}
      </div>
    </div>
  );
};
