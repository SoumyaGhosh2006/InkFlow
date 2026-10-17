/**
 * InkFlow Studio Zustand Store
 * Orchestrates dual-pane editor state, phased latency cycler, diff toggle, and evaluation scores.
 */

import { create } from 'zustand';
import type {
  InputType,
  RewriteContext,
  EvalsReport,
  RewriteResponse,
} from '../types/api';
import { rewriteApi } from '../lib/api';
import { useAuthStore } from './useAuthStore';

export type AppView = 'studio' | 'chat' | 'drill' | 'evolution' | 'pricing';

interface StudioState {
  // Navigation
  activeView: AppView;
  setActiveView: (view: AppView) => void;

  // Editor Inputs
  inputType: InputType;
  setInputType: (type: InputType) => void;
  context: RewriteContext;
  setContext: (context: RewriteContext) => void;
  inputDraft: string;
  setInputDraft: (text: string) => void;

  // Editor Outputs
  transformedDraft: string;
  setTransformedDraft: (text: string) => void;
  lastRewriteId: string | null;

  // Phased Cycler & Latency States
  isTransforming: boolean;
  cyclerStep: number;
  cyclerMessage: string;
  transformError: string | null;

  // Quality & Meaning Gate
  meaningCheckFailed: boolean;
  meaningWarning: string | null;

  // Evals & Provider Telemetry
  provider: string;
  evalScores: EvalsReport | null;

  // Visual Diff Toggle
  showDiff: boolean;
  setShowDiff: (show: boolean) => void;
  toggleDiff: () => void;

  // Pro Upgrade Modal & Mobile Stats Drawer
  isPricingModalOpen: boolean;
  setPricingModalOpen: (open: boolean) => void;
  isStatsDrawerOpen: boolean;
  setStatsDrawerOpen: (open: boolean) => void;
  mobileStudioTab: 'source' | 'output';
  setMobileStudioTab: (tab: 'source' | 'output') => void;

  // Actions
  triggerTransform: () => Promise<void>;
  acceptRewrite: () => Promise<void>;
  resetEditor: () => void;
  transferToHumanize: (text: string) => void;
}

const CYCLER_PHASES = [
  { step: 1, duration: 3000, text: 'Matching your sentence cadence and transitions...' },
  { step: 2, duration: 3000, text: 'Filtering synthetic AI buzzwords (Groq 120B)...' },
  { step: 3, duration: 3000, text: 'Verifying factual fidelity...' },
  { step: 4, duration: 4000, text: 'Switching to resilient backup model (Groq 20B)...' },
  { step: 5, duration: 2000, text: 'Applying light readability polish...' },
];

export const useStudioStore = create<StudioState>((set, get) => ({
  activeView: 'studio',
  setActiveView: (view) => set({ activeView: view }),

  inputType: 'raw_draft',
  setInputType: (type) => set({ inputType: type }),

  context: 'work_formal',
  setContext: (context) => set({ context }),

  inputDraft:
    'Furthermore, it is a testament to our dedication that we delve into the tapestry of solutions to optimize deliverables. In conclusion, this is crucial for our upcoming roadmap.',
  setInputDraft: (text) => set({ inputDraft: text }),

  transformedDraft: '',
  setTransformedDraft: (text) => set({ transformedDraft: text }),
  lastRewriteId: null,

  isTransforming: false,
  cyclerStep: 0,
  cyclerMessage: '',
  transformError: null,

  meaningCheckFailed: false,
  meaningWarning: null,

  provider: 'groq_gpt_oss_120b',
  evalScores: {
    slopReductionScore: 95.4,
    styleAlignmentScore: 89.2,
    semanticFidelityScore: 98.1,
    burstinessVariance: 12.4,
  },

  showDiff: false,
  setShowDiff: (show) => set({ showDiff: show }),
  toggleDiff: () => set((state) => ({ showDiff: !state.showDiff })),

  isPricingModalOpen: false,
  setPricingModalOpen: (open) => set({ isPricingModalOpen: open }),

  isStatsDrawerOpen: false,
  setStatsDrawerOpen: (open) => set({ isStatsDrawerOpen: open }),

  mobileStudioTab: 'source',
  setMobileStudioTab: (tab) => set({ mobileStudioTab: tab }),

  triggerTransform: async () => {
    const { inputDraft, inputType, context } = get();
    if (!inputDraft.trim()) return;

    // Gate transform activity: require user sign in
    const authStore = useAuthStore.getState();
    if (!authStore.isAuthenticated()) {
      authStore.openAuthModal('Sign in to humanize your writing draft and eliminate AI slop.');
      return;
    }

    set({
      isTransforming: true,
      transformError: null,
      mobileStudioTab: 'output',
      cyclerStep: 1,
      cyclerMessage: CYCLER_PHASES[0].text,
      meaningCheckFailed: false,
      meaningWarning: null,
    });

    // Start progressive loading cycler timers
    let timerIndex = 0;
    const interval = setInterval(() => {
      timerIndex += 1;
      if (timerIndex < CYCLER_PHASES.length) {
        set({
          cyclerStep: CYCLER_PHASES[timerIndex].step,
          cyclerMessage: CYCLER_PHASES[timerIndex].text,
        });
      }
    }, 2800);

    try {
      const response: RewriteResponse = await rewriteApi.transform({
        input: inputDraft,
        inputType,
        context,
        preserve_quirks: true,
      });

      clearInterval(interval);

      set({
        transformedDraft: response.finalOutput,
        meaningCheckFailed: Boolean(response.meaningCheckFailed),
        meaningWarning: response.meaningWarning || null,
        provider: response.provider || 'groq_gpt_oss_120b',
        evalScores: response.evalScores || null,
        lastRewriteId: response.rewrite_id || null,
        isTransforming: false,
        cyclerStep: 0,
        cyclerMessage: '',
      });

      // Update quota in Auth store
      if (response.words_consumed) {
        useAuthStore.getState().updateWordsUsed(response.words_consumed);
      }
    } catch (error: any) {
      clearInterval(interval);
      set({
        isTransforming: false,
        transformError: error.message || 'Transformation failed. Please try again.',
        cyclerStep: 0,
        cyclerMessage: '',
      });
    }
  },

  acceptRewrite: async () => {
    const { lastRewriteId, transformedDraft, meaningCheckFailed } = get();
    if (meaningCheckFailed) {
      // Invariant: If meaning check failed, strictly disallow feeding the Style Genome
      return;
    }

    if (lastRewriteId) {
      await rewriteApi.accept(lastRewriteId, transformedDraft);
    }
  },

  resetEditor: () => {
    set({
      inputDraft: '',
      transformedDraft: '',
      meaningCheckFailed: false,
      meaningWarning: null,
      showDiff: false,
      mobileStudioTab: 'source',
    });
  },

  transferToHumanize: (text: string) => {
    set({
      inputDraft: text,
      transformedDraft: '',
      meaningCheckFailed: false,
      meaningWarning: null,
      showDiff: false,
      mobileStudioTab: 'source',
      activeView: 'studio',
    });
  },
}));
