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

export const TransformationStudio: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col h-full bg-surface">
      {/* Top Bar with Context Pills & Quota */}
      <TopBar />

      {/* Dual Pane Main Canvas */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden border-b border-surface-border">
        {/* Left Pane: Source Editor with Slop Highlights */}
        <SourceEditor />

        {/* Right Pane: Twin Output with Diff & Cycler */}
        <OutputViewer />
      </div>

      {/* Bottom Telemetry & Action Dock */}
      <ActionDock />
    </div>
  );
};
