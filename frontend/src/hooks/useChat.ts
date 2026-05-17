import { useCallback } from 'react';
import axios from 'axios';
import { sendQuery } from '../api/medrag';
import { useChatStore } from '../store/chatStore';
import type { Message } from '../types';

function friendlyError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    if (status === 502 || status === 503 || !err.response) {
      return (
        'The backend server is not running.\n\n' +
        '▶ Start it with:\n' +
        '  cd backend\n' +
        '  pip install -r requirements.txt\n' +
        '  uvicorn app.main:app --reload --port 8000\n\n' +
        'Also make sure backend/.env is filled in with your API keys.'
      );
    }
    if (status === 500) {
      return (
        'Internal server error. Check that:\n' +
        '• backend/.env contains valid API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)\n' +
        '• Docker services are running: docker-compose up -d\n' +
        '• Check the backend terminal for the full error message.'
      );
    }
    if (err.code === 'ECONNABORTED') {
      return 'Request timed out. The RAG pipeline can take 10–30 seconds. Try again.';
    }
    return err.response?.data?.detail ?? err.message ?? 'Request failed.';
  }
  if (err instanceof Error) return err.message;
  return 'An unexpected error occurred.';
}

export function useChat() {
  const { addMessage, updateLastMessage, setLoading, isLoading } = useChatStore();

  const submit = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;

    const userMsg: Message = {
      id:        crypto.randomUUID(),
      role:      'user',
      content:   query.trim(),
      timestamp: new Date(),
    };
    addMessage(userMsg);

    const assistantMsg: Message = {
      id:        crypto.randomUUID(),
      role:      'assistant',
      content:   '',
      timestamp: new Date(),
    };
    addMessage(assistantMsg);
    setLoading(true);

    try {
      const response = await sendQuery(query.trim());
      updateLastMessage({ content: response.answer, response });
    } catch (err: unknown) {
      updateLastMessage({
        content: friendlyError(err),
        response: undefined,
      });
    } finally {
      setLoading(false);
    }
  }, [addMessage, updateLastMessage, setLoading, isLoading]);

  return { submit, isLoading };
}
