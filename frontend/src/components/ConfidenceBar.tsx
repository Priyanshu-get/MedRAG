import React from 'react';

interface ConfidenceBarProps {
  confidence: number;  // 0.0 – 1.0
  hasAnswer: boolean;
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ confidence, hasAnswer }) => {
  const pct = Math.round(confidence * 100);

  const { label, color, bgColor, glowColor } = (() => {
    if (!hasAnswer) return {
      label: 'No Evidence',
      color: 'var(--accent-red)',
      bgColor: 'rgba(248,113,113,0.12)',
      glowColor: 'rgba(248,113,113,0.3)',
    };
    if (pct >= 80) return {
      label: 'High Confidence',
      color: 'var(--accent-green)',
      bgColor: 'rgba(52,211,153,0.12)',
      glowColor: 'rgba(52,211,153,0.3)',
    };
    if (pct >= 65) return {
      label: 'Moderate Confidence',
      color: 'var(--accent-amber)',
      bgColor: 'rgba(251,191,36,0.12)',
      glowColor: 'rgba(251,191,36,0.3)',
    };
    return {
      label: 'Low Confidence',
      color: 'var(--accent-red)',
      bgColor: 'rgba(248,113,113,0.12)',
      glowColor: 'rgba(248,113,113,0.3)',
    };
  })();

  return (
    <div
      className="flex items-center gap-3 px-4 py-2 rounded-xl"
      style={{ background: bgColor, border: `1px solid ${glowColor}` }}
    >
      {/* Label */}
      <span className="text-xs font-semibold whitespace-nowrap" style={{ color }}>
        {label}
      </span>

      {/* Bar */}
      <div
        className="flex-1 h-1.5 rounded-full overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.07)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${hasAnswer ? pct : 0}%`,
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            boxShadow: `0 0 8px ${glowColor}`,
          }}
        />
      </div>

      {/* Percent */}
      <span className="text-xs font-mono font-bold" style={{ color }}>
        {hasAnswer ? `${pct}%` : '—'}
      </span>
    </div>
  );
};
