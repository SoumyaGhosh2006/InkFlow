/**
 * DrillCard Component
 * Implements the 60-Second Timed Voice Calibration Drill.
 *
 * Rationale:
 * Adheres to docs/frontend.md Section 3 View 1:
 * - 3 situational questions fetched from API.
 * - Radial 60s SVG countdown ring.
 * - Smooth horizontal Framer Motion slide transitions.
 * - Unlocks Style Genome via GenomeReveal celebratory modal.
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Sparkles, Loader2, RefreshCw } from 'lucide-react';
import { DrillCountdown } from './DrillCountdown';
import { GenomeReveal } from './GenomeReveal';
import { drillApi } from '../../lib/api';
import type { DrillPrompt, DrillAnswer, StyleGenomeResponse } from '../../types/api';

export const DrillCard: React.FC = () => {
  const [prompts, setPrompts] = useState<DrillPrompt[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentText, setCurrentText] = useState('');
  const [timeLeft, setTimeLeft] = useState(60);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [unlockedGenome, setUnlockedGenome] = useState<StyleGenomeResponse | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load scenarios on mount
  useEffect(() => {
    let mounted = true;
    const fetchScenarios = async () => {
      setIsLoading(true);
      const data = await drillApi.getPrompts();
      if (mounted) {
        setPrompts(data);
        setIsLoading(false);
        setTimeLeft(data[0]?.timeLimitSeconds || 60);
        setIsTimerRunning(true);
      }
    };
    fetchScenarios();
    return () => {
      mounted = false;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // 60-second countdown tick
  useEffect(() => {
    if (!isTimerRunning || isLoading) return;

    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          // Timer expired: auto-advance
          handleNextPrompt();
          return 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isTimerRunning, currentIndex, prompts, currentText]);

  const handleNextPrompt = async () => {
    if (prompts.length === 0) return;

    const currentPrompt = prompts[currentIndex];
    const updatedAnswers = {
      ...answers,
      [currentPrompt.id]: currentText.trim() || 'No answer provided in 60s.',
    };
    setAnswers(updatedAnswers);
    setCurrentText('');

    if (currentIndex < prompts.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setTimeLeft(prompts[currentIndex + 1]?.timeLimitSeconds || 60);
    } else {
      // All 3 completed — submit and unlock genome
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
  };

  const handleReset = () => {
    setCurrentIndex(0);
    setAnswers({});
    setCurrentText('');
    setTimeLeft(prompts[0]?.timeLimitSeconds || 60);
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
    scenario: 'Scenario 1',
    prompt: 'Write your natural response...',
    hint: 'Type instinctively.',
  };

  const wordCount = currentText.trim().split(/\s+/).filter(Boolean).length;

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
          className="text-xs text-ink-secondary hover:text-ink-primary flex items-center space-x-1"
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

              {/* Radial Countdown Ring */}
              <DrillCountdown timeLeft={timeLeft} totalTime={60} />
            </div>

            {/* Borderless Writing Canvas */}
            <div className="relative">
              <textarea
                value={currentText}
                onChange={(e) => setCurrentText(e.target.value)}
                placeholder="Start typing instinctively... Your natural rhythm, punctuation pauses, and phrasing will be analyzed."
                className="w-full h-44 p-4 text-base font-normal leading-relaxed text-ink-primary bg-canvas rounded-2xl border border-surface-border focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary transition-all resize-none placeholder:text-stone-400"
                autoFocus
              />

              {/* Word Count Indicator */}
              <div className="absolute bottom-3 right-4 text-xs font-mono text-ink-secondary bg-surface/80 backdrop-blur-xs px-2 py-1 rounded-md border border-stone-200/50">
                {wordCount} words
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-stone-400">
                Auto-advances when the 60s timer expires.
              </span>

              <button
                onClick={handleNextPrompt}
                disabled={isSubmitting}
                className="px-6 py-3 rounded-xl bg-ink-primary hover:bg-stone-800 disabled:bg-stone-300 text-white font-medium text-sm flex items-center space-x-2 shadow-sm transition-all"
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
                        : 'Next Scenario'}
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
