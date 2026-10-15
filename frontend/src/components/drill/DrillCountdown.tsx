/**
 * DrillCountdown Component
 * Radial 60-second SVG countdown ring.
 *
 * Rationale:
 * Wispr Flow aesthetic: precise circular SVG stroke-dashoffset animation
 * that visually guides authors to produce raw, instinctive drafts without overthinking.
 */

import React from 'react';

interface DrillCountdownProps {
  timeLeft: number;
  totalTime?: number;
}

export const DrillCountdown: React.FC<DrillCountdownProps> = ({
  timeLeft,
  totalTime = 60,
}) => {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.max(0, Math.min(1, timeLeft / totalTime));
  const strokeDashoffset = circumference - progress * circumference;

  // Visual urgency color transition
  const strokeColor =
    timeLeft <= 10
      ? '#EF4444' // Red warning
      : timeLeft <= 20
      ? '#F59E0B' // Amber caution
      : '#1C1917'; // Charcoal normal

  return (
    <div className="relative w-24 h-24 flex items-center justify-center select-none">
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 96 96">
        {/* Background track */}
        <circle
          cx="48"
          cy="48"
          r={radius}
          stroke="#E7E5E0"
          strokeWidth="4"
          fill="transparent"
        />
        {/* Animated countdown ring */}
        <circle
          cx="48"
          cy="48"
          r={radius}
          stroke={strokeColor}
          strokeWidth="4"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-linear"
        />
      </svg>

      {/* Numerical display in editorial serif */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-serif font-medium text-ink-primary">
          {timeLeft}
        </span>
        <span className="text-[10px] text-ink-secondary uppercase tracking-wider font-sans -mt-1">
          sec
        </span>
      </div>
    </div>
  );
};
