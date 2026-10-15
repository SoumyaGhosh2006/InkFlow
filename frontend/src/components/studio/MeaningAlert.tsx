/**
 * MeaningAlert Component
 * Amber warning banner displayed when backend meaningCheckFailed is true.
 *
 * Rationale:
 * Adheres strictly to docs/frontend.md Section 3 View 2 and docs/backend.md Section 4.4:
 * When Stage 3 semantic verification flags meaning drift, this soft warning banner unblocks
 * the user with "Copy Draft Anyway" and "Edit in Studio", while strictly disabling
 * "Accept & Learn" to protect the Style Genome from being poisoned by corrupted facts.
 */

import React from 'react';
import { AlertTriangle, Copy, Edit3, ShieldAlert } from 'lucide-react';
import { useStudioStore } from '../../store/useStudioStore';

interface MeaningAlertProps {
  onCopyAnyway: () => void;
  onEditInStudio: () => void;
}

export const MeaningAlert: React.FC<MeaningAlertProps> = ({
  onCopyAnyway,
  onEditInStudio,
}) => {
  const { meaningWarning } = useStudioStore();

  const warningMessage =
    meaningWarning ||
    "Meaning check couldn't fully verify this draft. Adaptive learning is paused for this rewrite to protect your Style Genome from drift.";

  return (
    <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-300 text-amber-950 space-y-3 shadow-sm animate-in fade-in duration-200">
      <div className="flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-accent-primary flex-shrink-0 mt-0.5" />
        <div className="space-y-1 flex-1">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center space-x-1.5">
            <span>Semantic Fidelity Warning</span>
            <span className="px-1.5 py-0.5 rounded-full bg-amber-200/80 text-[10px] font-mono text-amber-900">
              Genome Guard Active
            </span>
          </h4>
          <p className="text-xs text-amber-900/90 leading-relaxed font-sans">
            {warningMessage}
          </p>
        </div>
      </div>

      {/* Action Options */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-amber-200/70">
        <div className="flex items-center space-x-1.5 text-[11px] text-amber-800">
          <ShieldAlert className="w-3.5 h-3.5 text-accent-hover" />
          <span>"Accept & Learn" is safely disabled for this draft.</span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={onEditInStudio}
            className="px-3 py-1.5 rounded-lg bg-surface text-amber-900 hover:bg-amber-100 border border-amber-300 text-xs font-semibold flex items-center space-x-1.5 shadow-xs transition-colors"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit in Studio</span>
          </button>

          <button
            onClick={onCopyAnyway}
            className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-stone-900 text-xs font-semibold flex items-center space-x-1.5 shadow-xs transition-colors"
          >
            <Copy className="w-3.5 h-3.5 text-stone-900" />
            <span>Copy Draft Anyway</span>
          </button>
        </div>
      </div>
    </div>
  );
};
