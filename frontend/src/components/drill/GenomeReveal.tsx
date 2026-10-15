/**
 * GenomeReveal Component
 * Celebratory "Voice Profile Unlocked" modal with canvas-confetti
 * and visual breakdown of calibrated Style Genome metrics.
 *
 * Rationale:
 * Rewards the author immediately upon completing the 3-question drill
 * by proving the engine extracted real stylistic fingerprint variables.
 */

import React, { useEffect } from 'react';
import confetti from 'canvas-confetti';
import { Sparkles, ArrowRight, CheckCircle2, Shield } from 'lucide-react';
import type { StyleGenomeResponse } from '../../types/api';
import { useStudioStore } from '../../store/useStudioStore';

interface GenomeRevealProps {
  genome: StyleGenomeResponse;
  onClose: () => void;
}

export const GenomeReveal: React.FC<GenomeRevealProps> = ({ genome, onClose }) => {
  const { setActiveView } = useStudioStore();

  useEffect(() => {
    // Launch celebratory confetti burst
    confetti({
      particleCount: 100,
      spread: 75,
      origin: { y: 0.55 },
      colors: ['#F59E0B', '#10B981', '#1C1917', '#E7E5E0'],
    });
  }, []);

  const b = genome.baselineGenome;

  const handleGoToStudio = () => {
    onClose();
    setActiveView('studio');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-surface rounded-3xl border border-surface-border shadow-panel p-8 space-y-6 animate-in zoom-in-95 duration-200">
        {/* Header Icon & Title */}
        <div className="text-center space-y-2">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-amber-50 text-accent-primary flex items-center justify-center shadow-subtle border border-amber-200/80">
            <Sparkles className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-serif font-medium text-ink-primary">
            Voice Profile Unlocked
          </h2>
          <p className="text-sm text-ink-secondary max-w-md mx-auto">
            Your unique writing rhythm has been synthesized into an adaptive Style Genome twin.
          </p>
        </div>

        {/* Style Genome Metric Cards Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-2xl bg-canvas border border-surface-border">
            <span className="text-xs uppercase tracking-wider text-ink-secondary block">
              Sentence Cadence
            </span>
            <span className="text-2xl font-serif text-ink-primary font-medium mt-1 block">
              {b.avgSentenceLength} <span className="text-sm font-sans font-normal text-stone-500">words/sent</span>
            </span>
            <span className="text-[11px] text-stone-500 mt-1 block">
              Variance: ±{b.sentenceLengthVariance}w (natural burstiness)
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-canvas border border-surface-border">
            <span className="text-xs uppercase tracking-wider text-ink-secondary block">
              Formality Calibrated
            </span>
            <span className="text-2xl font-serif text-ink-primary font-medium mt-1 block">
              {b.formalityScore} <span className="text-sm font-sans font-normal text-stone-500">/ 10</span>
            </span>
            <span className="text-[11px] text-emerald-600 mt-1 block flex items-center space-x-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>Multi-context enabled</span>
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-canvas border border-surface-border">
            <span className="text-xs uppercase tracking-wider text-ink-secondary block">
              Vocabulary Richness (TTR)
            </span>
            <span className="text-2xl font-serif text-ink-primary font-medium mt-1 block">
              {Math.round(b.vocabularyRichnessTTR * 100)}%
            </span>
            <span className="text-[11px] text-stone-500 mt-1 block">
              Diverse phrasing, zero robotic repetition
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-canvas border border-surface-border">
            <span className="text-xs uppercase tracking-wider text-ink-secondary block">
              Punctuation Quirks
            </span>
            <div className="flex items-center space-x-2 mt-2">
              <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-xs font-mono font-medium border border-emerald-200">
                — Em-dash
              </span>
              <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-xs font-mono font-medium border border-emerald-200">
                ; Semicolon
              </span>
            </div>
            <span className="text-[11px] text-stone-500 mt-1 block">
              Strictly preserved in rewrites
            </span>
          </div>
        </div>

        {/* Favorite Transitions Pill List */}
        <div className="p-4 rounded-2xl bg-canvas border border-surface-border space-y-2">
          <span className="text-xs uppercase tracking-wider text-ink-secondary block">
            Detected Conversational Anchors
          </span>
          <div className="flex flex-wrap gap-2">
            {b.transitionHabits.map((habit, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-xl bg-surface border border-stone-200 text-xs text-ink-primary font-medium"
              >
                "{habit}"
              </span>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-2">
          <button
            onClick={handleGoToStudio}
            className="w-full py-3.5 px-4 rounded-xl bg-ink-primary hover:bg-stone-800 text-white font-medium text-sm flex items-center justify-center space-x-2 shadow-sm transition-all"
          >
            <span>Launch Transformation Studio</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Privacy Note */}
        <div className="flex items-center justify-center space-x-1.5 text-[11px] text-ink-muted">
          <Shield className="w-3.5 h-3.5 text-stone-400" />
          <span>Genome stored safely under your user ID in MongoDB Atlas</span>
        </div>
      </div>
    </div>
  );
};
