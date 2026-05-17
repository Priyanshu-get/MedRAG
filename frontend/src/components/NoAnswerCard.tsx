import React from 'react';
import { AlertTriangle, Search, RefreshCw } from 'lucide-react';

interface NoAnswerCardProps {
  answer: string;
  confidence: number;
  onRetry?: () => void;
}

const EXAMPLE_REFINEMENTS = [
  'Try using official medical terminology (e.g., "myocardial infarction" instead of "heart attack")',
  'Add context like treatment guidelines, year, or patient population',
  'Break complex questions into simpler, focused queries',
  'Include the drug class or condition name specifically',
];

export const NoAnswerCard: React.FC<NoAnswerCardProps> = ({ answer, confidence, onRetry }) => {
  return (
    <div className="animate-slide-up rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(248,113,113,0.05)',
        border: '1px solid rgba(248,113,113,0.2)',
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4"
        style={{ borderBottom: '1px solid rgba(248,113,113,0.15)' }}
      >
        <div className="flex items-center justify-center w-9 h-9 rounded-xl"
          style={{ background: 'rgba(248,113,113,0.15)' }}
        >
          <AlertTriangle size={18} color="var(--accent-red)" />
        </div>
        <div>
          <p className="text-sm font-semibold" style={{ color: 'var(--accent-red)' }}>
            No Sufficient Evidence Found
          </p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Evidence confidence: {confidence > 0 ? `${Math.round(confidence * 100)}%` : 'None'}
          </p>
        </div>
      </div>

      {/* Answer text */}
      <div className="px-5 py-4">
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {answer}
        </p>
      </div>

      {/* Refinement tips */}
      <div className="px-5 pb-4">
        <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)' }}>
          <div className="flex items-center gap-2 mb-3">
            <Search size={13} color="var(--text-muted)" />
            <span className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: 'var(--text-muted)' }}
            >
              Tips to refine your query
            </span>
          </div>
          <ul className="space-y-2">
            {EXAMPLE_REFINEMENTS.map((tip, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ background: 'var(--text-muted)' }}
                />
                <span className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  {tip}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Actions */}
      {onRetry && (
        <div className="px-5 pb-5">
          <button
            onClick={onRetry}
            className="flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-lg transition-all"
            style={{
              background: 'rgba(248,113,113,0.12)',
              border: '1px solid rgba(248,113,113,0.25)',
              color: 'var(--accent-red)',
            }}
          >
            <RefreshCw size={13} />
            Try a different query
          </button>
        </div>
      )}

      {/* Medical professional notice */}
      <div className="px-5 pb-5">
        <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          🏥 Always consult a <strong style={{ color: 'var(--text-secondary)' }}>qualified healthcare
          professional</strong> for medical advice, diagnosis, or treatment.
        </p>
      </div>
    </div>
  );
};
