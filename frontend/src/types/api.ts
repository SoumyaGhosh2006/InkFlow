/**
 * InkFlow API Type Definitions
 * Aligned with docs/backend.md and docs/frontend.md.
 */

export type UserTier = 'free' | 'pro';

export interface UserProfile {
  id: string;
  firebaseUid?: string;
  email: string;
  displayName?: string;
  tier: UserTier;
  wordsUsedThisWeek: number;
  weeklyWordLimit: number;
  lastWeekReset: string;
  streakDays: number;
  is_active?: boolean;
}

export interface DrillPrompt {
  id: string;
  scenario: string;
  prompt: string;
  timeLimitSeconds?: number;
  hint?: string;
  context?: string;
}

export interface DrillAnswer {
  question_id: string;
  text: string;
}

export interface DrillSubmitRequest {
  answers: DrillAnswer[];
}

export interface StyleGenomeBaseline {
  avgSentenceLength: number;
  sentenceLengthVariance: number;
  formalityScore: number;
  vocabularyRichnessTTR: number;
  transitionHabits: string[];
  punctuationHabits: {
    commaFrequency: string;
    emDashUsage: string;
    parenthesesUsage: string;
  };
}

export interface StyleGenomeResponse {
  id?: string;
  userId: string;
  version: number;
  baselineGenome: StyleGenomeBaseline;
  contextProfiles?: {
    work_formal?: { formalityOffset: number };
    academic_educator?: { formalityOffset: number };
    workplace_chat?: { formalityOffset: number };
  };
  exemplars?: string[];
  recentEditsBuffer?: Array<{
    rewriteId: string;
    timestamp: string;
    editType: string;
    detail: string;
  }>;
}

export type InputType = 'raw_draft' | 'bullet_points';
export type RewriteContext = 'work_formal' | 'academic' | 'chat';

export interface RewriteRequest {
  input: string;
  inputType: InputType;
  context: RewriteContext;
  preserve_quirks?: boolean;
}

export interface EvalsReport {
  slopReductionScore: number;
  styleAlignmentScore: number;
  semanticFidelityScore: number;
  burstinessVariance: number;
}

export interface RewriteStageLog {
  stage: string;
  input_text: string;
  output_text: string;
  duration_ms: number;
  provider_used: string;
  status: string;
  notes?: string;
}

export interface RewriteResponse {
  finalOutput: string;
  meaningCheckFailed: boolean;
  meaningWarning?: string | null;
  provider: 'groq_gpt_oss_120b' | 'groq_gpt_oss_20b' | string;
  evalScores: EvalsReport;
  stages?: RewriteStageLog[];
  words_consumed?: number;
  quota_remaining?: number;
  rewrite_id?: string;
}

export interface RewriteAcceptRequest {
  rewriteId: string;
  finalUserText: string;
}

export interface EvolutionAnalytics {
  streakDays: number;
  wordsUsedThisWeek: number;
  weeklyWordLimit: number | null;
  totalRewritesEvaluated: number;
  averageEvalScores: {
    slopReductionScore: number;
    styleAlignmentScore: number;
    semanticFidelityScore: number;
    burstinessVariance: number;
  };
  vocabularyGrowthCurve: Array<{
    session: number;
    uniqueTerms: number;
    richnessTTR: number;
  }>;
  styleGenome?: StyleGenomeResponse | null;
  adaptiveShifts?: Array<{
    session: string;
    shift: string;
    impact: string;
    status: 'incorporated' | 'stabilizing';
  }>;
}

export interface RazorpayOrderResponse {
  order_id: string;
  amount: number;
  currency: string;
  key_id?: string;
}
