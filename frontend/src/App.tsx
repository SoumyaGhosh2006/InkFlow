/**
 * App Component
 * Top-level application shell uniting NavigationDock, AppHeader,
 * the 4 active views, and StatsSidebar.
 *
 * Rationale:
 * Adheres strictly to docs/frontend.md Section 2 (Global Layout Architecture):
 * [ 48px Dock ] [ Main Dynamic View (Studio/Drill/Evolution) ] [ 320px Stats Sidebar ]
 */

import React, { useEffect } from 'react';
import { NavigationDock } from './components/layout/NavigationDock';
import { AppHeader } from './components/layout/AppHeader';
import { StatsSidebar } from './components/layout/StatsSidebar';
import { TransformationStudio } from './components/studio/TransformationStudio';
import { ChatWriterView } from './components/chat/ChatWriterView';
import { DrillCard } from './components/drill/DrillCard';
import { WritingEvolutionView } from './components/evolution/WritingEvolutionView';
import { UpgradeModal } from './components/payments/UpgradeModal';
import { useStudioStore } from './store/useStudioStore';
import { useAuthStore } from './store/useAuthStore';
import { onAuthChange } from './lib/firebase';

export const App: React.FC = () => {
  const {
    activeView,
    setActiveView,
    setPricingModalOpen,
    isStatsDrawerOpen,
    setStatsDrawerOpen,
  } = useStudioStore();
  const { fetchUser } = useAuthStore();

  useEffect(() => {
    // Synchronize auth state and bearer token with Firebase auth events
    const unsubscribe = onAuthChange(async (fbUser) => {
      if (fbUser) {
        try {
          const token = await fbUser.getIdToken();
          localStorage.setItem('inkflow_token', token);
          await fetchUser();
        } catch (e) {
          console.warn('Failed to refresh Firebase token:', e);
        }
      }
    });

    fetchUser();
    return () => {
      if (typeof unsubscribe === 'function') unsubscribe();
    };
  }, [fetchUser]);

  // If user navigates to pricing view directly, pop the upgrade modal and return view to studio
  useEffect(() => {
    if (activeView === 'pricing') {
      setPricingModalOpen(true);
      setActiveView('studio');
    }
  }, [activeView, setActiveView, setPricingModalOpen]);

  const renderActiveView = () => {
    switch (activeView) {
      case 'studio':
      case 'pricing':
        return <TransformationStudio />;
      case 'chat':
        return <ChatWriterView />;
      case 'drill':
        return (
          <div className="flex-1 bg-canvas flex flex-col overflow-y-auto">
            <DrillCard />
          </div>
        );
      case 'evolution':
        return <WritingEvolutionView />;
      default:
        return <TransformationStudio />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-canvas text-ink-primary font-sans antialiased">
      {/* 48px Icon-Only Navigation Dock (Desktop) / Bottom Nav Bar (Mobile) */}
      <NavigationDock />

      {/* Main Workspace Column */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden pb-16 md:pb-0">
        {/* App Header */}
        <AppHeader />

        {/* Dynamic View Canvas */}
        <main className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
          {renderActiveView()}
        </main>
      </div>

      {/* Right Insights & Stats Sidebar (Desktop) */}
      <div className="hidden xl:flex h-full shrink-0">
        <StatsSidebar />
      </div>

      {/* Mobile Slide-over Drawer for Stats & Quota (< xl screens) */}
      {isStatsDrawerOpen && (
        <div className="fixed inset-0 z-50 xl:hidden flex justify-end">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setStatsDrawerOpen(false)}
            aria-label="Close stats drawer overlay"
          />
          <div className="relative w-80 max-w-[85vw] h-full bg-surface shadow-2xl z-10 flex flex-col animate-in slide-in-from-right duration-200">
            <StatsSidebar />
          </div>
        </div>
      )}

      {/* Global Pro Upgrade Modal */}
      <UpgradeModal />
    </div>
  );
};

export default App;
