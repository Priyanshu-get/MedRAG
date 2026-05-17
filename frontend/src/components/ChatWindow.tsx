import React, { useEffect, useRef } from 'react';
import { Trash2, Activity, Database, WifiOff, Loader } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { QueryInput } from './QueryInput';
import { useChatStore } from '../store/chatStore';
import { useChat } from '../hooks/useChat';
import { useBackendStatus } from '../hooks/useBackendStatus';

const WELCOME_SUGGESTIONS = [
  'First-line treatment for hypertension',
  'Metformin mechanism of action',
  'COVID-19 long-term effects',
  'Immunotherapy in NSCLC',
];

export const ChatWindow: React.FC = () => {
  const { messages, clearHistory } = useChatStore();
  const { submit, isLoading } = useChat();
  const { status, indexedDocs } = useBackendStatus();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const isEmpty = messages.length === 0;
  const backendOffline = status === 'offline';

  return (
    <div className="flex flex-col h-full">
      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between px-6 py-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-xl animate-glow"
            style={{
              background: 'linear-gradient(135deg, rgba(59,157,255,0.2), rgba(34,211,238,0.15))',
              border: '1px solid rgba(59,157,255,0.35)',
            }}
          >
            <Activity size={18} color="var(--accent-cyan)" />
          </div>
          <div>
            <h1 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
              MedRAG
            </h1>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Evidence-grounded medical query system
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Backend status badge */}
          {status === 'checking' && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-subtle)' }}
            >
              <Loader size={11} color="var(--text-muted)" className="animate-spin" />
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Connecting…</span>
            </div>
          )}
          {status === 'online' && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
              style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.2)' }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs font-semibold" style={{ color: 'var(--accent-green)' }}>
                {indexedDocs > 0 ? `${indexedDocs.toLocaleString()} docs` : 'Backend Online'}
              </span>
            </div>
          )}
          {status === 'offline' && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
              style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.25)' }}
            >
              <WifiOff size={11} color="var(--accent-red)" />
              <span className="text-xs font-semibold" style={{ color: 'var(--accent-red)' }}>Backend Offline</span>
            </div>
          )}

          {/* Clear button */}
          {!isEmpty && (
            <button
              onClick={clearHistory}
              className="p-2 rounded-xl transition-all"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-muted)',
              }}
              title="Clear conversation"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* ── Messages area ────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {isEmpty ? (
          /* Welcome screen */
          <div className="flex flex-col items-center justify-center h-full text-center space-y-8 animate-fade-in">
            {/* Hero icon */}
            <div className="relative">
              <div
                className="w-20 h-20 rounded-3xl flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, rgba(59,157,255,0.15), rgba(34,211,238,0.1))',
                  border: '1px solid rgba(59,157,255,0.25)',
                  boxShadow: '0 0 60px rgba(59,157,255,0.15)',
                }}
              >
                <Database size={34} color="var(--accent-cyan)" />
              </div>
              <div
                className="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center"
                style={{ background: 'var(--accent-green)' }}
              >
                <span className="text-xs font-bold text-white">✓</span>
              </div>
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Grounded Medical Evidence
              </h2>
              <p className="text-sm max-w-md" style={{ color: 'var(--text-secondary)' }}>
                Every answer is backed by peer-reviewed literature from PubMed, PMC, and Semantic Scholar.
                <span style={{ color: 'var(--accent-cyan)' }}> Zero hallucinations</span> — if evidence
                doesn't exist, we'll tell you.
              </p>
            </div>

            {/* Feature pills */}
            <div className="flex flex-wrap justify-center gap-2">
              {['PubMed', 'PMC Open Access', 'Semantic Scholar', 'ClinicalTrials.gov'].map((s) => (
                <span
                  key={s}
                  className="text-xs px-3 py-1.5 rounded-full font-medium"
                  style={{
                    background: 'rgba(59,157,255,0.08)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {s}
                </span>
              ))}
            </div>

            {/* Quick-start suggestions */}
            <div className="w-full max-w-lg space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider mb-3"
                style={{ color: 'var(--text-muted)' }}
              >
                Try asking about
              </p>
              {backendOffline && (
                <div className="text-xs px-4 py-3 rounded-xl mb-2"
                  style={{
                    background: 'rgba(248,113,113,0.08)',
                    border: '1px solid rgba(248,113,113,0.2)',
                    color: 'var(--accent-red)',
                  }}
                >
                  ⚠️ Backend is offline. Start it with:
                  <code className="block mt-1" style={{ color: 'var(--text-secondary)' }}>
                    cd backend &amp;&amp; uvicorn app.main:app --reload --port 8000
                  </code>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {WELCOME_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => submit(s)}
                    disabled={backendOffline}
                    className="text-left text-sm px-4 py-3 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--text-secondary)',
                    }}
                    onMouseEnter={(e) => {
                      if (!backendOffline) {
                        e.currentTarget.style.background = 'rgba(59,157,255,0.07)';
                        e.currentTarget.style.borderColor = 'var(--border-mid)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                      e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Conversation */
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ────────────────────────────────────────────────────────── */}
      <div
        className="px-6 pb-6 pt-4 flex-shrink-0"
        style={{ borderTop: '1px solid var(--border-subtle)' }}
      >
        <QueryInput onSubmit={submit} isLoading={isLoading} />
      </div>
    </div>
  );
};
