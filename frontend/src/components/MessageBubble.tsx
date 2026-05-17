import React from 'react';
import { User, Bot, ShieldCheck, Clock } from 'lucide-react';
import type { Message } from '../types';
import { ConfidenceBar } from './ConfidenceBar';
import { CitationCard } from './CitationCard';
import { NoAnswerCard } from './NoAnswerCard';
import { useChatStore } from '../store/chatStore';

interface MessageBubbleProps {
  message: Message;
  onCitationClick?: (index: number) => void;
}

function renderAnswerWithCitations(html: string): React.ReactNode {
  // Parse the HTML string to replace <cite data-source="N"> with styled spans
  const parts = html.split(/(<cite[^>]*>.*?<\/cite>)/gi);
  return parts.map((part, i) => {
    const citeMatch = part.match(/<cite data-source="(\d+)">(.*?)<\/cite>/i);
    if (citeMatch) {
      return (
        <cite key={i} data-source={citeMatch[1]}>
          {citeMatch[2]}
        </cite>
      );
    }
    // Render plain text, preserving newlines
    return part.split('\n').map((line, j) => (
      <React.Fragment key={`${i}-${j}`}>
        {j > 0 && <br />}
        {line}
      </React.Fragment>
    ));
  });
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const { setActiveCitation, activeCitationIndex } = useChatStore();
  const isUser = message.role === 'user';
  const resp   = message.response;

  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end animate-slide-up">
        <div
          className="max-w-[72%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm leading-relaxed"
          style={{
            background: 'linear-gradient(135deg, #1e4a8a, #0f3360)',
            border: '1px solid rgba(59,157,255,0.25)',
            color: 'var(--text-primary)',
          }}
        >
          {message.content}
        </div>
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
          style={{ background: 'rgba(59,157,255,0.15)', border: '1px solid rgba(59,157,255,0.25)' }}
        >
          <User size={14} color="var(--accent-blue)" />
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex items-start gap-3 animate-slide-up">
      {/* Avatar */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center animate-glow"
        style={{ background: 'rgba(34,211,238,0.12)', border: '1px solid rgba(34,211,238,0.3)' }}
      >
        <Bot size={14} color="var(--accent-cyan)" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-3">

        {/* Main answer bubble */}
        <div
          className="glass-card px-5 py-4"
          style={{ borderRadius: '4px 18px 18px 18px' }}
        >
          {/* Confidence bar (only for completed responses) */}
          {resp && (
            <div className="mb-4">
              <ConfidenceBar confidence={resp.confidence} hasAnswer={resp.has_answer} />
            </div>
          )}

          {/* Answer text */}
          {resp?.has_answer === false ? (
            <NoAnswerCard answer={message.content} confidence={resp.confidence} />
          ) : message.content ? (
            <div
              className="text-sm leading-relaxed prose-medical"
              style={{ color: 'var(--text-primary)' }}
            >
              {renderAnswerWithCitations(message.content)}
            </div>
          ) : (
            /* Typing indicator */
            <div className="flex items-center gap-1.5 py-1">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          )}

          {/* Disclaimer */}
          {resp && (
            <div
              className="flex items-start gap-2 mt-4 pt-3 text-xs leading-relaxed"
              style={{
                borderTop: '1px solid var(--border-subtle)',
                color: 'var(--text-muted)',
              }}
            >
              <ShieldCheck size={11} className="flex-shrink-0 mt-0.5" color="var(--accent-teal)" />
              {resp.disclaimer}
            </div>
          )}
        </div>

        {/* Citations sidebar (inline on assistant messages) */}
        {resp?.has_answer && resp.sources.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider px-1"
              style={{ color: 'var(--text-muted)' }}
            >
              {resp.sources.length} Source{resp.sources.length > 1 ? 's' : ''}
            </p>
            <div className="grid gap-2">
              {resp.sources.map((src, i) => (
                <CitationCard
                  key={src.chunk_id}
                  source={src}
                  index={i + 1}
                  isActive={activeCitationIndex === i + 1}
                  onClick={() => setActiveCitation(
                    activeCitationIndex === i + 1 ? null : i + 1
                  )}
                />
              ))}
            </div>
          </div>
        )}

        {/* Timestamp */}
        {resp && (
          <div className="flex items-center gap-1 px-1">
            <Clock size={9} color="var(--text-muted)" />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
