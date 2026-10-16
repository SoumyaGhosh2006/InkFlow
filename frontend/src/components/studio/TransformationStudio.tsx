/**
 * TransformationStudio Component
 * Primary workspace hosting dual-pane source and twin output editors.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 2:
 * Combines TopBar, SourceEditor, OutputViewer, and ActionDock into
 * a cohesive porcelain workstation.
 */

import React from 'react';
import { TopBar } from './TopBar';
import { SourceEditor } from './SourceEditor';
import { OutputViewer } from './OutputViewer';
import { ActionDock } from './ActionDock';
import { useStudioStore } from '../../store/useStudioStore';
import { PenLine, Sparkles, Loader2 } from 'lucide-react';

export const TransformationStudio: React.FC = () => {
  const { mobileStudioTab, setMobileStudioTab, transformedDraft, isTransforming } =
    useStudioStore();

  return (
    <div className="flex-1 flex flex-col h-full bg-surface overflow-hidden">
      {/* Top Bar with Context Pills & Quota */}
      <TopBar />

      {/* Mobile-Only Segmented View Selector (< lg screens) */}
      <div className="flex lg:hidden bg-canvas/90 border-b border-surface-border px-3 py-1.5 gap-2 shrink-0">
        <button
          onClick={() => setMobileStudioTab('source')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all cursor-pointer ${
            mobileStudioTab === 'source'
              ? 'bg-surface text-ink-primary shadow-xs border border-surface-border'
              : 'text-ink-secondary hover:text-ink-primary'
          }`}
        >
          <PenLine className="w-3.5 h-3.5" />
          <span>Source Draft</span>
        </button>

        <button
          onClick={() => setMobileStudioTab('output')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all cursor-pointer ${
            mobileStudioTab === 'output'
              ? 'bg-surface text-ink-primary shadow-xs border border-surface-border'
              : 'text-ink-secondary hover:text-ink-primary'
          }`}
        >
          {isTransforming ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-primary" />
          ) : (
            <Sparkles className="w-3.5 h-3.5 text-accent-primary" />
          )}
          <span>Humanized Result</span>
          {transformedDraft && !isTransforming && (
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse ml-1" />
          )}
        </button>
      </div>

      {/* Main Canvas: Single Full-Screen Pane on Mobile, Dual Side-by-Side on Desktop */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden border-b border-surface-border min-h-0">
        {/* Left Pane: Source Editor */}
        <div
          className={`flex-1 flex flex-col h-full min-h-0 ${
            mobileStudioTab === 'source' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          <SourceEditor />
        </div>

        {/* Right Pane: Twin Output */}
        <div
          className={`flex-1 flex flex-col h-full min-h-0 ${
            mobileStudioTab === 'output' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          <OutputViewer />
        </div>
      </div>

      {/* Bottom Telemetry & Action Dock (Visible on desktop or when on mobile output tab) */}
      <div className={mobileStudioTab === 'output' ? 'block' : 'hidden lg:block'}>
        <ActionDock />
      </div>
    </div>
  );
};
