import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Lightbulb } from 'lucide-react';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

const EXAMPLE_QUERIES = [
  'What is the first-line treatment for hypertension?',
  'Drug interactions between metformin and aspirin',
  'Efficacy of immunotherapy in non-small cell lung cancer',
  'What are the JNC 8 guidelines for blood pressure targets?',
  'Mechanism of action of ACE inhibitors',
];

export const QueryInput: React.FC<QueryInputProps> = ({ onSubmit, isLoading }) => {
  const [value, setValue] = useState('');
  const [showExamples, setShowExamples] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const MAX_CHARS = 2000;

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 180)}px`;
  }, [value]);

  const handleSubmit = () => {
    const q = value.trim();
    if (!q || isLoading || q.length < 3) return;
    onSubmit(q);
    setValue('');
    setShowExamples(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleExample = (query: string) => {
    setValue(query);
    setShowExamples(false);
    textareaRef.current?.focus();
  };

  const charRatio = value.length / MAX_CHARS;
  const charColor = charRatio > 0.9 ? 'var(--accent-red)'
    : charRatio > 0.7 ? 'var(--accent-amber)'
    : 'var(--text-muted)';

  return (
    <div className="relative">
      {/* Example queries dropdown */}
      {showExamples && !isLoading && (
        <div
          className="absolute bottom-full mb-2 left-0 right-0 rounded-2xl overflow-hidden z-10 animate-slide-up"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-mid)',
            boxShadow: 'var(--shadow-deep)',
          }}
        >
          <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Example queries
            </span>
          </div>
          {EXAMPLE_QUERIES.map((q, i) => (
            <button
              key={i}
              onClick={() => handleExample(q)}
              className="w-full text-left px-4 py-3 text-sm transition-colors"
              style={{ color: 'var(--text-secondary)', borderBottom: i < EXAMPLE_QUERIES.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(59,157,255,0.06)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input container */}
      <div
        className="flex items-end gap-3 rounded-2xl p-3 transition-all duration-200"
        style={{
          background: 'var(--bg-card)',
          border: `1px solid ${value ? 'var(--border-glow)' : 'var(--border-subtle)'}`,
          boxShadow: value ? 'var(--shadow-glow)' : 'none',
        }}
      >
        {/* Example queries toggle */}
        <button
          onClick={() => setShowExamples((v) => !v)}
          disabled={isLoading}
          className="flex-shrink-0 mb-0.5 p-2 rounded-xl transition-all disabled:opacity-40"
          style={{
            background: showExamples ? 'rgba(59,157,255,0.15)' : 'rgba(255,255,255,0.04)',
            border: '1px solid var(--border-subtle)',
            color: showExamples ? 'var(--accent-blue)' : 'var(--text-muted)',
          }}
          title="Show example queries"
        >
          <Lightbulb size={15} />
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          id="medical-query-input"
          value={value}
          onChange={(e) => setValue(e.target.value.slice(0, MAX_CHARS))}
          onKeyDown={handleKeyDown}
          placeholder="Ask a medical question… (e.g., 'first-line treatment for type 2 diabetes')"
          rows={1}
          disabled={isLoading}
          className="flex-1 resize-none bg-transparent text-sm leading-relaxed placeholder:text-sm disabled:opacity-60 outline-none"
          style={{
            color: 'var(--text-primary)',
            fontFamily: 'Inter, sans-serif',
          }}
        />

        {/* Char count + Send */}
        <div className="flex-shrink-0 flex flex-col items-end gap-1.5 mb-0.5">
          {value.length > 0 && (
            <span className="text-xs font-mono" style={{ color: charColor }}>
              {value.length}/{MAX_CHARS}
            </span>
          )}
          <button
            id="send-query-btn"
            onClick={handleSubmit}
            disabled={!value.trim() || isLoading || value.length < 3}
            className="flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: value.trim() && !isLoading
                ? 'linear-gradient(135deg, var(--accent-blue), var(--accent-cyan))'
                : 'rgba(255,255,255,0.06)',
              boxShadow: value.trim() && !isLoading
                ? '0 0 20px rgba(59,157,255,0.3)' : 'none',
            }}
          >
            {isLoading ? (
              <Loader2 size={16} color="var(--text-muted)" className="animate-spin" />
            ) : (
              <Send size={15} color={value.trim() ? '#fff' : 'var(--text-muted)'} />
            )}
          </button>
        </div>
      </div>

      {/* Hint text */}
      <p className="text-xs mt-2 text-center" style={{ color: 'var(--text-muted)' }}>
        Press <kbd className="px-1.5 py-0.5 rounded text-xs font-mono"
          style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid var(--border-subtle)' }}
        >Enter</kbd> to send · <kbd className="px-1.5 py-0.5 rounded text-xs font-mono"
          style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid var(--border-subtle)' }}
        >Shift + Enter</kbd> for newline
      </p>
    </div>
  );
};
