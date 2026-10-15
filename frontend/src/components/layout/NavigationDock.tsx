/**
 * NavigationDock Component
 * 48px wide icon-only left dock with Radix tooltips and keyboard shortcuts (⌘1, ⌘2, ⌘3).
 *
 * Rationale:
 * Wispr Flow aesthetic — keeps the viewport ultra-clean and distraction-free.
 * Accessible tooltips emerge on short hover delays to orient authors instantly.
 */

import React, { useEffect } from 'react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { PenSquare, Zap, BarChart3, CreditCard, Sparkles } from 'lucide-react';
import { useStudioStore, type AppView } from '../../store/useStudioStore';

interface NavItem {
  id: AppView;
  icon: React.ElementType;
  label: string;
  shortcut: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'studio',
    icon: PenSquare,
    label: 'Transformation Studio',
    shortcut: '⌘1',
  },
  {
    id: 'drill',
    icon: Zap,
    label: 'Voice Calibration Drill',
    shortcut: '⌘2',
  },
  {
    id: 'evolution',
    icon: BarChart3,
    label: 'Writing Evolution & Evals',
    shortcut: '⌘3',
  },
  {
    id: 'pricing',
    icon: CreditCard,
    label: 'Pro Subscription',
    shortcut: '⌘4',
  },
];

export const NavigationDock: React.FC = () => {
  const { activeView, setActiveView, isPricingModalOpen, setPricingModalOpen } = useStudioStore();

  // Register global ⌘1, ⌘2, ⌘3, ⌘4 keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        if (e.key === '1') {
          e.preventDefault();
          setActiveView('studio');
        } else if (e.key === '2') {
          e.preventDefault();
          setActiveView('drill');
        } else if (e.key === '3') {
          e.preventDefault();
          setActiveView('evolution');
        } else if (e.key === '4') {
          e.preventDefault();
          setPricingModalOpen(true);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setActiveView, setPricingModalOpen]);

  return (
    <Tooltip.Provider delayDuration={150}>
      <aside className="w-14 flex-shrink-0 flex flex-col items-center justify-between py-6 bg-surface border-r border-surface-border z-20 select-none">
        {/* Top Logo Glyph */}
        <div className="flex flex-col items-center space-y-6">
          <button
            onClick={() => setActiveView('studio')}
            className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 to-amber-400 flex items-center justify-center text-white shadow-subtle hover:scale-105 transition-transform"
            aria-label="InkFlow Home"
          >
            <Sparkles className="w-5 h-5" />
          </button>

          {/* Navigation Items List */}
          <nav className="flex flex-col items-center space-y-3" aria-label="Main Navigation">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.id === 'pricing' ? isPricingModalOpen : activeView === item.id;

              return (
                <Tooltip.Root key={item.id}>
                  <Tooltip.Trigger asChild>
                    <button
                      onClick={() => {
                        if (item.id === 'pricing') {
                          setPricingModalOpen(true);
                        } else {
                          setActiveView(item.id);
                        }
                      }}
                      className={`relative w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
                        isActive
                          ? 'bg-amber-50 text-accent-primary font-semibold shadow-sm'
                          : 'text-ink-secondary hover:text-ink-primary hover:bg-surface-subtle'
                      }`}
                      aria-label={`${item.label} (${item.shortcut})`}
                    >
                      <Icon className="w-5 h-5 stroke-[1.8]" />
                      {isActive && (
                        <span className="absolute -left-1 top-2.5 bottom-2.5 w-1 bg-accent-primary rounded-r-full" />
                      )}
                    </button>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="right"
                      sideOffset={12}
                      className="px-3 py-1.5 bg-stone-900 text-stone-100 text-xs font-medium rounded-lg shadow-panel flex items-center space-x-2 animate-in fade-in zoom-in-95 z-50"
                    >
                      <span>{item.label}</span>
                      <kbd className="px-1.5 py-0.5 bg-stone-800 text-stone-300 rounded text-[10px] font-mono border border-stone-700">
                        {item.shortcut}
                      </kbd>
                      <Tooltip.Arrow className="fill-stone-900" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              );
            })}
          </nav>
        </div>

        {/* Bottom Help / Status Marker */}
        <div className="flex flex-col items-center space-y-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Backend connected" />
          <span className="text-[10px] text-ink-muted font-mono">v1.0</span>
        </div>
      </aside>
    </Tooltip.Provider>
  );
};
