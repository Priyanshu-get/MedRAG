import axios from 'axios';
import type { ChatResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120_000,  // 2 min — RAG pipeline can take time
  headers: { 'Content-Type': 'application/json' },
});

export async function sendQuery(
  query: string,
  maxSources = 5
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', {
    query,
    max_sources: maxSources,
  });
  return data;
}

export async function triggerIngest(
  topic: string,
  maxResults = 50,
  sources: string[] = ['pubmed']
) {
  const { data } = await api.post('/ingest', {
    topic,
    max_results: maxResults,
    sources,
  });
  return data;
}

export async function getHealth() {
  const { data } = await api.get('/health');
  return data;
}
