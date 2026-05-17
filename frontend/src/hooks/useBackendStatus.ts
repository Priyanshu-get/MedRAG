import { useState, useEffect } from 'react';
import { getHealth } from '../api/medrag';

type Status = 'checking' | 'online' | 'offline';

export function useBackendStatus() {
  const [status, setStatus] = useState<Status>('checking');
  const [indexedDocs, setIndexedDocs] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const data = await getHealth();
        if (!cancelled) {
          setStatus('online');
          setIndexedDocs(data.indexed_documents ?? 0);
        }
      } catch {
        if (!cancelled) setStatus('offline');
      }
    }

    check();
    const interval = setInterval(check, 30_000); // re-check every 30s
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return { status, indexedDocs };
}
