/**
 * OutputViewer Component
 * Right pane presenting transformed output, phased loading cycler, and character diffs.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 2:
 * - 5-phase progressive status animation (0-3s cadence, 3-6s slop filter, 6-9s fidelity, 9-13s+ Groq failover backup, final polish).
 * - Shimmer pulse across output pane during inference.
 * - MeaningAlert guard when meaningCheckFailed is true.
 * - Toggleable character-level diff visualizing punctuation preservation.
 */

import React, { useState } from 'react';
import { GitCompare, Sparkles, Loader2, Check } from 'lucide-react';
import { useStudioStore } from '../../store/useStudioStore';
import { CharacterDiff } from './CharacterDiff';
import { MeaningAlert } from './MeaningAlert';

export const OutputViewer: React.FC = () => {
  const {
    inputDraft,
    transformedDraft,
    setTransformedDraft,
    isTransforming,
    cyclerStep,
    cyclerMessage,
    meaningCheckFailed,
    showDiff,
    toggleDiff,
  } = useStudioStore();

  const [copiedNotice, setCopiedNotice] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const handleCopyAnyway = () => {
    if (!transformedDraft) return;
    navigator.clipboard.writeText(transformedDraft);
    setCopiedNotice(true);
    setTimeout(() => setCopiedNotice(false), 2500);
  };

  const handleEditInStudio = () => {
    setIsEditing(true);
  };

  return (
    <div className="flex-1 flex flex-col bg-surface overflow-hidden">
      {/* Pane Header */}
      <div className="px-6 py-3 border-b border-surface-border flex items-center justify-between bg-canvas/40">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">
            InkFlow Twin Output
          </span>
          {transformedDraft && !isTransforming && (
            <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-medium flex items-center space-x-1">
              <Check className="w-3 h-3 text-emerald-600" />
              <span>Voice Matched</span>
            </span>
          )}
        </div>

        {/* Diff Toggle Button */}
        {transformedDraft && !isTransforming && (
          <div className="flex items-center space-x-2">
            <button
              onClick={toggleDiff}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg text-xs font-medium border transition-all ${
                showDiff
                  ? 'bg-amber-100 text-amber-900 border-amber-300 font-semibold shadow-2xs'
                  : 'bg-surface text-ink-secondary hover:text-ink-primary border-stone-200'
              }`}
            >
              <GitCompare className="w-3.5 h-3.5" />
              <span>{showDiff ? 'Hide Diff' : 'Show What Changed'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Pane Content */}
      <div className="flex-1 p-6 overflow-y-auto space-y-4 relative">
        {/* Active Phased Cycler Animation State */}
        {isTransforming && (
          <div className="h-full min-h-[320px] rounded-2xl p-8 flex flex-col items-center justify-center space-y-6 shimmer-active border border-amber-200/50">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center text-accent-primary animate-pulse">
                <Loader2 className="w-8 h-8 animate-spin text-accent-primary" />
              </div>
              <span className="absolute -top-1 -right-1 px-1.5 py-0.5 rounded-full bg-stone-900 text-amber-400 text-[10px] font-mono font-bold">
                {cyclerStep}/5
              </span>
            </div>

            <div className="text-center space-y-2 max-w-sm">
              <p className="text-sm font-semibold text-ink-primary font-sans">
                {cyclerMessage || 'Personalizing your draft...'}
              </p>
              <p className="text-xs text-stone-500">
                Executing 4-stage pipeline with Groq deep reasoning & factual verification.
              </p>
            </div>

            {/* Stage Progress indicators */}
            <div className="flex items-center space-x-2">
              {[1, 2, 3, 4, 5].map((step) => (
                <div
                  key={step}
                  className={`h-1.5 rounded-full transition-all duration-500 ${
                    step <= cyclerStep ? 'w-6 bg-accent-primary' : 'w-2 bg-stone-200'
                  }`}
                />
              ))}
            </div>
          </div>
        )}

        {/* Quality Alert when Meaning Check Failed */}
        {!isTransforming && meaningCheckFailed && (
          <MeaningAlert
            onCopyAnyway={handleCopyAnyway}
            onEditInStudio={handleEditInStudio}
          />
        )}

        {/* Empty State before first transformation */}
        {!isTransforming && !transformedDraft && (
          <div className="h-full min-h-[320px] flex flex-col items-center justify-center text-center p-8 space-y-4 text-stone-400">
            <div className="w-12 h-12 rounded-2xl bg-surface-subtle flex items-center justify-center text-stone-400 border border-surface-border">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-ink-primary">
                Your writing twin is standby.
              </p>
              <p className="text-xs text-ink-secondary max-w-xs">
                Enter your draft or outline on the left and click "Transform Draft" to see personal cadence and punctuation preservation in action.
              </p>
            </div>
          </div>
        )}

        {/* Transformed Output / Diff View */}
        {!isTransforming && transformedDraft && (
          <>
            {showDiff ? (
              <CharacterDiff
                originalText={inputDraft}
                transformedText={transformedDraft}
              />
            ) : isEditing ? (
              <textarea
                value={transformedDraft}
                onChange={(e) => setTransformedDraft(e.target.value)}
                className="w-full h-80 p-4 text-base font-normal leading-relaxed text-ink-primary bg-canvas rounded-2xl border border-surface-border focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary resize-none font-sans"
              />
            ) : (
              <div
                onClick={() => setIsEditing(true)}
                className="p-5 rounded-2xl bg-canvas border border-surface-border font-sans text-base leading-relaxed text-ink-primary select-text cursor-text min-h-[220px]"
                title="Click to edit draft directly"
              >
                {transformedDraft}
              </div>
            )}
          </>
        )}

        {/* Copied Feedback Toast */}
        {copiedNotice && (
          <div className="absolute top-4 right-4 px-3 py-1.5 rounded-lg bg-stone-900 text-stone-100 text-xs font-medium shadow-panel flex items-center space-x-1.5 animate-in fade-in">
            <Check className="w-3.5 h-3.5 text-emerald-400" />
            <span>Copied to clipboard</span>
          </div>
        )}
      </div>
    </div>
  );
};
