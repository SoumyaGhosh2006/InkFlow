/**
 * DrillCard Component
 * Implements the 2-Minute Timed Voice Calibration Drill.
 *
 * Rationale:
 * Adheres to linguistic calibration guidelines (Pennebaker & King, Boston Cookie Theft,
 * Labov & Waletzky, Procedural instruction):
 * - 4 research-backed scenarios fetched from API.
 * - 120-second (2-minute) radial countdown ring.
 * - Image display for visual descriptive scenarios (e.g. Boston Cookie Theft Task).
 * - Mandatory answer validation: author must provide an answer before advancing.
 * - Unlocks Style Genome via GenomeReveal celebratory modal.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Sparkles, Loader2, RefreshCw, AlertCircle } from 'lucide-react';
import { DrillCountdown } from './DrillCountdown';
import { GenomeReveal } from './GenomeReveal';
import { drillApi } from '../../lib/api';
import type { DrillPrompt, DrillAnswer, StyleGenomeResponse } from '../../types/api';

const DEFAULT_DRILL_TIME_SECONDS = 120; // 2 minutes

export const DrillCard: React.FC = () => {
  const [prompts, setPrompts] = useState<DrillPrompt[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentText, setCurrentText] = useState('');
  const [timeLeft, setTimeLeft] = useState(DEFAULT_DRILL_TIME_SECONDS);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [unlockedGenome, setUnlockedGenome] = useState<StyleGenomeResponse | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Load scenarios on mount
  useEffect(() => {
    let mounted = true;
    const fetchScenarios = async () => {
      setIsLoading(true);
      const data = await drillApi.getPrompts();
      if (mounted) {
        setPrompts(data);
        setIsLoading(false);
        setTimeLeft(data[0]?.timeLimitSeconds || DEFAULT_DRILL_TIME_SECONDS);
        setIsTimerRunning(true);
      }
    };
    fetchScenarios();
    return () => {
      mounted = false;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const currentTextRef = useRef(currentText);
  useEffect(() => {
    currentTextRef.current = currentText;
  }, [currentText]);

  const advanceScenario = useCallback(async (forcedAnswer?: string) => {
    if (prompts.length === 0) return;

    const currentPrompt = prompts[currentIndex];
    const textToSave = forcedAnswer !== undefined ? forcedAnswer : currentTextRef.current.trim();
    
    const updatedAnswers = {
      ...answers,
      [currentPrompt.id]: textToSave,
    };
    setAnswers(updatedAnswers);
    setCurrentText('');
    setValidationError(null);

    if (currentIndex < prompts.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setTimeLeft(prompts[currentIndex + 1]?.timeLimitSeconds || DEFAULT_DRILL_TIME_SECONDS);
    } else {
      // All scenarios completed — submit and unlock genome
      setIsTimerRunning(false);
      setIsSubmitting(true);

      const formattedAnswers: DrillAnswer[] = Object.entries(updatedAnswers).map(
        ([qid, text]) => ({
          question_id: qid,
          text,
        })
      );

      try {
        const genome = await drillApi.submitDrill(formattedAnswers);
        setUnlockedGenome(genome);
      } catch (err) {
        console.error('Calibration error:', err);
      } finally {
        setIsSubmitting(false);
      }
    }
  }, [answers, currentIndex, prompts]);

  const advanceScenarioRef = useRef(advanceScenario);
  useEffect(() => {
    advanceScenarioRef.current = advanceScenario;
  }, [advanceScenario]);

  // Handle manual click to Next Question with mandatory validation
  const handleNextClick = () => {
    const trimmed = currentText.trim();
    if (!trimmed) {
      setValidationError('Please type your answer to this question before moving forward.');
      textareaRef.current?.focus();
      return;
    }
    setValidationError(null);
    advanceScenario();
  };

  // 120-second countdown tick
  useEffect(() => {
    if (!isTimerRunning || isLoading) return;

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          // If time expires and user has written something, advance automatically
          if (currentTextRef.current.trim()) {
            advanceScenarioRef.current();
            return DEFAULT_DRILL_TIME_SECONDS;
          }
          // If empty, pause at 0 and urge the user to answer
          setValidationError("Time's up for this question! Please enter your quick thoughts to proceed.");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isTimerRunning, isLoading]);

  const handleReset = () => {
    setCurrentIndex(0);
    setAnswers({});
    setCurrentText('');
    setValidationError(null);
    setTimeLeft(prompts[0]?.timeLimitSeconds || DEFAULT_DRILL_TIME_SECONDS);
    setIsTimerRunning(true);
    setUnlockedGenome(null);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-stone-500 space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-accent-primary" />
        <span className="text-sm font-medium">Preparing Voice Calibration scenarios...</span>
      </div>
    );
  }

  const currentPrompt = prompts[currentIndex] || {
    id: 'scenario_1',
    scenario: 'Stream of Consciousness',
    prompt: "Write whatever is on your mind right now. Don't edit.",
    hint: 'Pennebaker & King 1999 — reveals small words, sentence length, and emotion words.',
  };

  const wordCount = currentText.trim().split(/\s+/).filter(Boolean).length;
  const totalLimit = currentPrompt.timeLimitSeconds || DEFAULT_DRILL_TIME_SECONDS;

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-4xl mx-auto w-full">
      {/* Calibration Progress Bar */}
      <div className="w-full flex items-center justify-between mb-8 px-2">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-accent-primary" />
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-primary">
            Scenario {currentIndex + 1} of {prompts.length}
          </span>
        </div>

        {/* Step dots */}
        <div className="flex items-center space-x-2">
          {prompts.map((_, idx) => (
            <div
              key={idx}
              className={`h-2 rounded-full transition-all duration-300 ${
                idx === currentIndex
                  ? 'w-8 bg-accent-primary'
                  : idx < currentIndex
                  ? 'w-2 bg-emerald-500'
                  : 'w-2 bg-stone-200'
              }`}
            />
          ))}
        </div>

        <button
          onClick={handleReset}
          className="text-xs text-ink-secondary hover:text-ink-primary flex items-center space-x-1 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>
      </div>

      {/* Main Card with Smooth Horizontal Framer Motion Transitions */}
      <div className="w-full bg-surface rounded-3xl border border-surface-border shadow-panel p-8 relative overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="space-y-6"
          >
            {/* Top Prompt Row with Radial Countdown */}
            <div className="flex items-start justify-between gap-6 pb-4 border-b border-surface-border">
              <div className="space-y-2 flex-1">
                <span className="px-2.5 py-1 rounded-lg bg-surface-subtle text-ink-secondary text-xs font-medium uppercase tracking-wide">
                  {currentPrompt.scenario}
                </span>
                <h2 className="text-xl md:text-2xl font-serif font-medium text-ink-primary leading-snug">
                  {currentPrompt.prompt}
                </h2>
                <p className="text-xs text-ink-secondary italic">
                  💡 {currentPrompt.hint}
                </p>
              </div>

              {/* Radial Countdown Ring (120s / 2 Minutes) */}
              <DrillCountdown timeLeft={timeLeft} totalTime={totalLimit} />
            </div>

            {/* Stimulus Image if provided (e.g. Boston Cookie Theft) */}
            {currentPrompt.imageUrl && (
              <div className="w-full flex flex-col items-center justify-center p-3 bg-stone-50 rounded-2xl border border-stone-200/80">
                <img
                  src={currentPrompt.imageUrl}
                  alt={currentPrompt.scenario}
                  className="max-h-60 object-contain rounded-lg shadow-xs"
                />
                <span className="text-[11px] text-stone-500 mt-1.5 italic font-sans">
                  Stimulus drawing from Boston Diagnostic Aphasia Examination (Goodglass & Kaplan, 1972)
                </span>
              </div>
            )}

            {/* Borderless Writing Canvas */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={currentText}
                onChange={(e) => {
                  setCurrentText(e.target.value);
                  if (validationError) setValidationError(null);
                }}
                placeholder="Start typing instinctively... Your natural rhythm, sentence lengths, and word choices will calibrate your Style Genome."
                className={`w-full h-44 p-4 text-base font-normal leading-relaxed text-ink-primary bg-canvas rounded-2xl border transition-all resize-none placeholder:text-stone-400 focus:outline-none focus:ring-2 ${
                  validationError
                    ? 'border-red-400 focus:ring-red-200'
                    : 'border-surface-border focus:ring-accent-primary/20 focus:border-accent-primary'
                }`}
                autoFocus
              />

              {/* Word Count Indicator */}
              <div className="absolute bottom-3 right-4 text-xs font-mono text-ink-secondary bg-surface/80 backdrop-blur-xs px-2 py-1 rounded-md border border-stone-200/50">
                {wordCount} words
              </div>
            </div>

            {/* Validation Error Prompt */}
            {validationError && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center space-x-2 animate-in fade-in">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-600" />
                <span className="font-medium">{validationError}</span>
              </div>
            )}

            {/* Bottom Actions */}
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-stone-400">
                2-minute timed response. Answers are required to calibrate accurately.
              </span>

              <button
                onClick={handleNextClick}
                disabled={isSubmitting}
                className="px-6 py-3 rounded-xl bg-ink-primary hover:bg-stone-800 disabled:bg-stone-300 text-white font-medium text-sm flex items-center space-x-2 shadow-sm transition-all cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Calibrating Style Genome...</span>
                  </>
                ) : (
                  <>
                    <span>
                      {currentIndex === prompts.length - 1
                        ? 'Finish Calibration'
                        : 'Next Question'}
                    </span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Celebratory Genome Modal */}
      {unlockedGenome && (
        <GenomeReveal
          genome={unlockedGenome}
          onClose={() => setUnlockedGenome(null)}
        />
      )}
    </div>
  );
};
