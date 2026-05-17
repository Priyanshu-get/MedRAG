import { create } from 'zustand';
import type { Message } from '../types';

interface ChatStore {
  messages: Message[];
  isLoading: boolean;
  activeCitationIndex: number | null;

  addMessage:        (msg: Message) => void;
  updateLastMessage: (partial: Partial<Message>) => void;
  setLoading:        (v: boolean) => void;
  setActiveCitation: (idx: number | null) => void;
  clearHistory:      () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages:           [],
  isLoading:          false,
  activeCitationIndex: null,

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  updateLastMessage: (partial) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length === 0) return s;
      msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...partial };
      return { messages: msgs };
    }),

  setLoading: (v) => set({ isLoading: v }),

  setActiveCitation: (idx) => set({ activeCitationIndex: idx }),

  clearHistory: () => set({ messages: [], activeCitationIndex: null }),
}));
