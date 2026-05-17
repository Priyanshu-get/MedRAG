export interface SourceMetadata {
  chunk_id: string;
  title: string;
  authors: string[];
  authors_short: string;
  journal: string;
  pub_date: string;
  doi?: string;
  pmid?: string;
  url?: string;
  citation_url?: string;
  abstract_snippet: string;
  rerank_score: number;
}

export interface ChatResponse {
  query: string;
  answer: string;
  sources: SourceMetadata[];
  confidence: number;
  has_answer: boolean;
  source_count: number;
  disclaimer: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: ChatResponse;
}
