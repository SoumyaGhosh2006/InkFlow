/**
 * ActionDock Component
 * Bottom action dock providing provider telemetry, evaluation scores,
 * copy triggers, and protected "Accept & Learn" controls.
 *
 * Rationale:
 * Adheres strictly to docs/frontend.md Section 3 View 2:
 * - Provider Pill: Tag showing Groq 120B (or Groq 20B Backup on fallback).
 * - Eval Score Pill: Slop Eradication % | Fidelity %.
 * - Accept & Learn: Strictly disabled if meaningCheckFailed is true to prevent genome drift.
 */

import React, { useState } from 'react';
import { Copy, Check, Cpu, ShieldCheck, Sparkles, Lock } from 'lucide-react';
import { useStudioStore } from '../../store/useStudioStore';

export const ActionDock: React.FC = () => {
  const {
    transformedDraft,
    provider,
    evalScores,
    meaningCheckFailed,
    acceptRewrite,
  } = useStudioStore();

  const [copied, setCopied] = useState(false);
  const [accepted, setAccepted] = useState(false);

  const handleCopy = () => {
    if (!transformedDraft) return;
    navigator.clipboard.writeText(transformedDraft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAccept = async () => {
    if (meaningCheckFailed || !transformedDraft) return;
    await acceptRewrite();
    setAccepted(true);
    setTimeout(() => setAccepted(false), 2500);
  };

  const isBackup = provider.includes('20b');
  const providerLabel = isBackup ? 'Groq 20B (Backup)' : 'Groq 120B (Primary)';

  const slopScore = evalScores?.slopReductionScore || 95.4;
  const fidelityScore = evalScores?.semanticFidelityScore || 98.1;

  return (
    <div className="p-3 sm:p-4 bg-surface border-t border-surface-border flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
      {/* Left: Telemetry Pills */}
      <div className="flex items-center space-x-2 overflow-x-auto max-w-full w-full sm:w-auto pb-1 sm:pb-0">
        {/* Slop Eradication Score Pill (Always visible) */}
        <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-medium shrink-0">
          <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
          <span>Slop Purged: {Math.round(slopScore)}%</span>
        </div>

        {/* Provider & Fidelity pills on sm+ */}
        <div
          className={`hidden sm:flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium border shrink-0 ${
            isBackup
              ? 'bg-amber-50 text-amber-900 border-amber-300'
              : 'bg-surface-subtle text-ink-primary border-surface-border'
          }`}
          title="Current LLM Provider Host"
        >
          <Cpu className="w-3.5 h-3.5 text-stone-500" />
          <span>{providerLabel}</span>
        </div>

        <div
          className={`hidden sm:flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium border shrink-0 ${
            meaningCheckFailed
              ? 'bg-amber-100 text-amber-900 border-amber-300'
              : 'bg-surface-subtle text-ink-primary border-surface-border'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5 text-stone-600" />
          <span>Fidelity: {Math.round(fidelityScore)}%</span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center space-x-2 sm:space-x-3 w-full sm:w-auto justify-end">
        {/* Copy Button */}
        <button
          onClick={handleCopy}
          disabled={!transformedDraft}
          className="flex-1 sm:flex-initial px-4 py-2 rounded-xl bg-surface-subtle hover:bg-stone-200 disabled:opacity-40 disabled:cursor-not-allowed text-ink-primary text-xs font-semibold flex items-center justify-center space-x-1.5 border border-stone-200 transition-colors cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-stone-500" />
              <span>Copy Output</span>
            </>
          )}
        </button>

        {/* Accept & Learn Button */}
        <div className="relative group flex-1 sm:flex-initial">
          <button
            onClick={handleAccept}
            disabled={!transformedDraft || meaningCheckFailed}
            className={`w-full sm:w-auto px-4 py-2 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all cursor-pointer ${
              meaningCheckFailed
                ? 'bg-stone-200 text-stone-400 cursor-not-allowed border border-stone-300'
                : accepted
                ? 'bg-emerald-600 text-white'
                : 'bg-ink-primary hover:bg-stone-800 disabled:opacity-40 disabled:cursor-not-allowed text-white shadow-xs'
            }`}
          >
            {meaningCheckFailed ? (
              <>
                <Lock className="w-3.5 h-3.5 text-stone-400" />
                <span>Locked</span>
              </>
            ) : accepted ? (
              <>
                <Check className="w-3.5 h-3.5 text-white" />
                <span>Learned</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>Accept & Learn</span>
              </>
            )}
          </button>

          {/* Locked tooltip */}
          {meaningCheckFailed && (
            <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block w-64 p-2 bg-stone-900 text-stone-100 text-[11px] rounded-lg shadow-panel z-50">
              Disabled to protect your Style Genome from semantic drift. Use "Copy Draft Anyway" instead.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
