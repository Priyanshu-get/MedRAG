import React from 'react';
import { ExternalLink, Users, BookOpen, Calendar, FileText } from 'lucide-react';
import type { SourceMetadata } from '../types';

interface CitationCardProps {
  source: SourceMetadata;
  index: number;
  isActive?: boolean;
  onClick?: () => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  source, index, isActive, onClick,
}) => {
  const { title, authors_short, journal, pub_date, citation_url, abstract_snippet, doi, pmid, rerank_score } = source;

  const scoreColor = rerank_score > 1.5
    ? 'var(--accent-green)'
    : rerank_score > 0.5
      ? 'var(--accent-amber)'
      : 'var(--accent-blue)';

  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-xl transition-all duration-200 animate-fade-in"
      style={{
        background: isActive
          ? 'rgba(59,157,255,0.10)'
          : 'rgba(255,255,255,0.03)',
        border: isActive
          ? '1px solid rgba(59,157,255,0.35)'
          : '1px solid var(--border-subtle)',
        padding: '14px 16px',
        boxShadow: isActive ? '0 0 20px rgba(59,157,255,0.12)' : 'none',
      }}
    >
      {/* Source badge + score */}
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs font-bold px-2 py-0.5 rounded-md"
          style={{
            background: 'rgba(59,157,255,0.15)',
            border: '1px solid rgba(59,157,255,0.25)',
            color: 'var(--accent-blue)',
          }}
        >
          Source {index}
        </span>

        {rerank_score > 0 && (
          <span className="text-xs font-mono" style={{ color: scoreColor }}>
            ↑ {rerank_score.toFixed(2)}
          </span>
        )}
      </div>

      {/* Title */}
      <h4
        className="text-sm font-semibold leading-snug mb-2 line-clamp-2"
        style={{ color: 'var(--text-primary)' }}
      >
        {citation_url ? (
          <a
            href={citation_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="hover:underline"
            style={{ color: 'var(--accent-cyan)' }}
          >
            {title}
          </a>
        ) : title}
      </h4>

      {/* Meta row */}
      <div className="flex flex-wrap gap-3 mb-2">
        {authors_short && (
          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <Users size={10} />
            {authors_short}
          </span>
        )}
        {journal && (
          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <BookOpen size={10} />
            {journal}
          </span>
        )}
        {pub_date && (
          <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <Calendar size={10} />
            {pub_date}
          </span>
        )}
      </div>

      {/* Abstract snippet */}
      {abstract_snippet && (
        <p
          className="text-xs leading-relaxed mb-3 line-clamp-3"
          style={{ color: 'var(--text-muted)' }}
        >
          <FileText size={9} className="inline mr-1 opacity-60" />
          {abstract_snippet}
        </p>
      )}

      {/* Links row */}
      <div className="flex items-center gap-3">
        {doi && (
          <a
            href={`https://doi.org/${doi}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-xs transition-colors hover:opacity-100 opacity-70"
            style={{ color: 'var(--accent-teal)' }}
          >
            <ExternalLink size={10} />
            DOI
          </a>
        )}
        {pmid && (
          <a
            href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-xs transition-colors hover:opacity-100 opacity-70"
            style={{ color: 'var(--accent-teal)' }}
          >
            <ExternalLink size={10} />
            PubMed
          </a>
        )}
      </div>
    </div>
  );
};
